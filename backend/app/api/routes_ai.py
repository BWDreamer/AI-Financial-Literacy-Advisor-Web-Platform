import json
import logging
import re
from collections.abc import AsyncIterator

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    status,
    UploadFile,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.ai.dependencies import get_ai_advisor_service
from app.ai.exceptions import (
    LLMConfigurationError,
    LLMRateLimitError,
    LLMServiceError,
)
from app.ai.prompts import build_advisory_topic_instructions
from app.api.dependencies import get_current_user
from app.core.database import get_db
from app.core.config import settings
from app.models.financial_rule import FinancialRule
from app.models.user import User
from app.repositories.financial_repository import (
    list_assets,
    list_cash_flows,
    list_debts,
    list_recurring_cash_flows,
)
from app.repositories.rule_repository import get_financial_rule_by_id
from app.repositories.chat_repository import add_message, get_conversation
from app.repositories.goal_repository import (
    get_goal,
    save_confirmed_goal_plan,
)
from app.schemas.ai import (
    AIChatRequest,
    AIChatResponse,
    AIPdfChatResponse,
)
from app.services.admin_service import get_advisory_settings
from app.services.ai_advisor_service import AIAdvisorService
from app.services.chat_context_service import (
    build_conversation_context,
    build_goal_conversation_context,
)
from app.services.financial_service import (
    FinancialPlanningSnapshot,
    build_financial_planning_context,
    build_financial_planning_snapshot,
)
from app.services.goal_allocation_service import (
    build_goal_allocation_context,
)
from app.services.goal_intent_clarification_service import (
    GOAL_INTENT_CLARIFICATION_RESPONSE_SCHEMA,
    GoalIntentClarification,
    GoalIntentClarificationStatus,
    build_emergency_fund_amount_question,
    build_goal_intent_clarification_prompt,
    emergency_fund_bare_amount_clarification,
    normalize_goal_intent_clarification,
    pending_emergency_fund_amount,
    resolve_emergency_fund_amount_answer,
)
from app.services.goal_planning_service import (
    GOAL_PLANNING_STATE_RESPONSE_SCHEMA,
    GoalPlanningState,
    GoalRecommendationStatus,
    build_goal_dialogue_context,
    build_goal_state_correction_prompt,
    build_goal_state_extraction_prompt,
    goal_state_payload_is_complete,
    is_goal_planning_follow_up,
    normalize_goal_planning_state,
)
from app.services.goal_service import (
    ConfirmedGoalPlan,
    build_confirmed_goal_plan,
)
from app.services.goal_review_service import (
    build_goal_review_context,
    build_goal_review_message,
)
from app.services.memory_service import (
    MEMORY_EXTRACTION_RESPONSE_SCHEMA,
    ExtractedMemory,
    build_memory_context,
    build_memory_extraction_prompt,
    get_memory_snapshot,
    normalize_memory_extraction_payload,
    remember_from_conversation_turn,
    retrieve_relevant_memories,
)
from app.services.pdf_asset_classifier import (
    ASSET_CLASSIFICATION_RESPONSE_SCHEMA,
    AssetCandidate,
    build_asset_classification_prompt,
    normalize_asset_classification_payload,
)
from app.services.pdf_cash_flow_classifier import (
    CASH_FLOW_KIND_RESPONSE_SCHEMA,
    CashFlowKindCandidate,
    build_cash_flow_kind_prompt,
    normalize_cash_flow_kind_payload,
)
from app.services.pdf_financial_service import (
    AmbiguousTransactionCandidate,
    PdfExtractionError,
    build_pdf_ai_context,
    build_transaction_classification_prompt,
    imported_records_to_api,
    parse_transaction_classification_response,
    process_financial_pdf,
)
from app.services.financial_rule_intents import (
    FINANCIAL_RULE_INTENT_RESPONSE_SCHEMA,
    build_financial_rule_intent_prompt,
    normalize_financial_rule_intent_payload,
)
from app.services.rule_lookup_service import (
    build_financial_rule_context_from_intent,
)

router = APIRouter()
logger = logging.getLogger(__name__)
PDF_MODEL_CONTEXT = "pdf-financial-parser"
GOAL_PLANNING_PATTERN = re.compile(
    r"\b(?:my|our|financial|money)\s+goals?\b|"
    r"\b(?:i want|i need|i would like|i'd like|help me|plan|planning)\b"
    r".{0,80}\b(?:save|saving|buy|purchase|emergency fund|pay off|repay|"
    r"debt|home deposit|retire|retirement|budget|cash flow)\b|"
    r"\b(?:save|saving) for\b|\bbuild an? emergency fund\b|"
    r"\bpay off (?:my |our )?debt\b",
    re.IGNORECASE | re.DOTALL,
)


@router.get("/ping")
def ping_ai():
    return {
        "module": "ai",
        "status": "ok",
    }


def _build_selected_rule_context(rule: FinancialRule) -> str:
    return "\n".join(
        [
            (
                "Verified financial rule context from the structured "
                "rules knowledge base:"
            ),
            f"Rule value: {rule.rule_value}",
            f"Region: {rule.region}.",
            f"Category: {rule.category}.",
            f"Financial year: {rule.rule_year}.",
            f"Rule key: {rule.rule_key}.",
            (
                f"Source: {rule.source_name or 'Not provided'} "
                f"({rule.source_url or 'Not provided'})."
            ),
            (
                "When answering, use this verified rule context as "
                "the source of truth, include a brief rationale, "
                "cite the source, and keep the answer educational."
            ),
        ]
    )


def _build_grounded_message(
    *,
    user_message: str,
    memory_context: str | None,
    conversation_context: str | None,
    financial_context: str | None,
    goal_planning_context: str | None,
    rule_context: str | None,
    goal_review_context: str | None = None,
) -> str:
    context_sections = [
        context
        for context in (
            memory_context,
            conversation_context,
            financial_context,
            goal_review_context,
            goal_planning_context,
            rule_context,
        )
        if context is not None
    ]

    if not context_sections:
        return user_message

    return "\n\n".join(
        context_sections
        + [
            "User question:",
            user_message,
        ]
    )


def _financial_snapshot_for_user(
    db: Session,
    user_id: int,
) -> FinancialPlanningSnapshot:
    return build_financial_planning_snapshot(
        list_assets(db, user_id),
        list_debts(db, user_id),
        list_cash_flows(db, user_id),
        list_recurring_cash_flows(db, user_id),
    )


def _financial_context_from_snapshot(
    snapshot: FinancialPlanningSnapshot,
    include_empty: bool,
) -> str | None:
    if not snapshot.has_financial_records and not include_empty:
        return None
    return build_financial_planning_context(snapshot)


def _is_goal_planning_discussion(
    user_message: str,
    conversation_context: str | None,
) -> bool:
    discussion = "\n".join(
        context
        for context in (conversation_context, user_message)
        if context
    )
    return (
        GOAL_PLANNING_PATTERN.search(discussion) is not None
        or is_goal_planning_follow_up(conversation_context)
    )


async def _extract_goal_planning_state(
    advisor_service: AIAdvisorService,
    conversation_context: str | None,
    user_message: str,
    memory_context: str | None,
    financial_context: str | None,
) -> GoalPlanningState:
    extraction_prompt = build_goal_state_extraction_prompt(
        conversation_context,
        user_message,
        memory_context,
        financial_context,
    )
    payload = await advisor_service.reply_json(
        extraction_prompt,
        GOAL_PLANNING_STATE_RESPONSE_SCHEMA,
    )
    if not goal_state_payload_is_complete(payload):
        payload = await advisor_service.reply_json(
            build_goal_state_correction_prompt(extraction_prompt, payload),
            GOAL_PLANNING_STATE_RESPONSE_SCHEMA,
        )
    if not goal_state_payload_is_complete(payload):
        raise LLMServiceError(
            "The AI provider returned an incomplete goal recommendation."
        )
    return normalize_goal_planning_state(payload)


async def _clarify_goal_intent(
    advisor_service: AIAdvisorService,
    conversation_context: str | None,
    last_assistant_message: str | None,
    user_message: str,
) -> GoalIntentClarification:
    resolved_amount = resolve_emergency_fund_amount_answer(
        last_assistant_message,
        user_message,
    )
    if resolved_amount is not None:
        return resolved_amount

    bare_amount = emergency_fund_bare_amount_clarification(
        user_message,
        conversation_context,
    )
    if bare_amount is not None:
        return bare_amount

    reply_json = getattr(advisor_service, "reply_json", None)
    if reply_json is None:
        return GoalIntentClarification(GoalIntentClarificationStatus.CLEAR)

    payload = await reply_json(
        build_goal_intent_clarification_prompt(
            conversation_context,
            user_message,
        ),
        GOAL_INTENT_CLARIFICATION_RESPONSE_SCHEMA,
    )
    clarification = normalize_goal_intent_clarification(payload)
    pending_amount = pending_emergency_fund_amount(last_assistant_message)
    if (
        pending_amount is not None
        and clarification.status == GoalIntentClarificationStatus.CLEAR
    ):
        return GoalIntentClarification(
            GoalIntentClarificationStatus.NEEDS_CLARIFICATION,
            clarifying_question=build_emergency_fund_amount_question(
                pending_amount
            ),
        )
    return clarification


def _build_goal_workflow_context(
    state: GoalPlanningState | None,
    snapshot: FinancialPlanningSnapshot,
    confirmed_goals_available: bool = False,
) -> str:
    dialogue_context = build_goal_dialogue_context(state, snapshot)
    if dialogue_context is not None:
        return dialogue_context
    if state is None:
        raise ValueError("Completed goal planning requires extracted goal state.")
    return build_goal_allocation_context(
        state,
        snapshot,
        awaiting_approval=(
            state.recommendation_status
            == GoalRecommendationStatus.NEEDS_RECOMMENDATION
        ),
        confirmed_goals_available=confirmed_goals_available,
    )


def _prepare_confirmed_goal_plan(
    state: GoalPlanningState | None,
    user_id: int,
    conversation_id: int | None,
) -> ConfirmedGoalPlan | None:
    if (
        state is None
        or state.recommendation_status != GoalRecommendationStatus.ACCEPTED
        or conversation_id is None
    ):
        return None
    try:
        return build_confirmed_goal_plan(state, user_id)
    except (KeyError, ValueError) as error:
        raise LLMServiceError(
            "The confirmed goal plan could not be converted into MyGoals records."
        ) from error


def _llm_http_error(error: Exception) -> HTTPException:
    if isinstance(error, LLMConfigurationError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The AI service is not configured. "
                "Set the configured provider API key on the backend."
            ),
        )

    if isinstance(error, LLMRateLimitError):
        return HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "The AI provider rate limit was reached. "
                "Please wait a moment and try again."
            ),
        )

    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=(
            "The AI service could not generate a response. "
            "Please try again."
        ),
    )


def _raise_llm_http_error(error: Exception) -> None:
    raise _llm_http_error(error) from error


def _formatted_answer(answer: str) -> str:
    cleaned_lines: list[str] = []

    for raw_line in answer.splitlines():
        line = raw_line.strip()

        if not line:
            if cleaned_lines and cleaned_lines[-1]:
                cleaned_lines.append("")
            continue

        if re.fullmatch(r"[-_]{3,}", line):
            continue

        if re.fullmatch(
            r"(?i)(?:#{1,6}\s*)?ai analysis[:：]?",
            line,
        ):
            continue

        line = re.sub(
            r"(?i)^ai analysis\s*[:：-]?\s*",
            "",
            line,
        ).strip()

        line = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
        line = line.replace("```", "").replace("`", "")
        line = re.sub(r"<[^>]+>", "", line)
        line = re.sub(r"__([^_\n]+)__", r"**\1**", line)

        heading = re.match(r"^(#{1,6})\s*(.+)$", line)
        if heading:
            heading_marker = "##" if len(heading.group(1)) <= 2 else "###"
            line = f"{heading_marker} {heading.group(2).strip()}"
        else:
            line = re.sub(r"^\s*[-*+]\s+", "- ", line)
            line = re.sub(r"^\s*(\d+)[.)]\s+", r"\1. ", line)

        if line:
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


def _validate_pdf_upload(file: UploadFile, content: bytes) -> None:
    filename = file.filename or "uploaded.pdf"
    content_type = (file.content_type or "").lower()
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported.",
        )

    if content_type and content_type not in {
        "application/pdf",
        "application/octet-stream",
    }:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported.",
        )

    if len(content) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "The uploaded PDF is too large. "
                f"Maximum size is {settings.max_upload_size_mb} MB."
            ),
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded PDF is empty.",
        )


async def _classify_pdf_transactions(
    advisor_service: AIAdvisorService,
    candidates: list[AmbiguousTransactionCandidate],
):
    response = await advisor_service.reply(
        build_transaction_classification_prompt(
            candidates,
        )
    )

    return parse_transaction_classification_response(
        response,
        candidates,
    )


async def _classify_pdf_cash_flow_kinds(
    advisor_service: AIAdvisorService,
    candidates: list[CashFlowKindCandidate],
):
    payload = await advisor_service.reply_json(
        build_cash_flow_kind_prompt(candidates),
        CASH_FLOW_KIND_RESPONSE_SCHEMA,
    )

    return normalize_cash_flow_kind_payload(payload, candidates)


async def _classify_pdf_assets(
    advisor_service: AIAdvisorService,
    candidates: list[AssetCandidate],
):
    payload = await advisor_service.reply_json(
        build_asset_classification_prompt(candidates),
        ASSET_CLASSIFICATION_RESPONSE_SCHEMA,
    )

    classifications = normalize_asset_classification_payload(
        payload,
        candidates,
    )
    if len(classifications) != len(candidates):
        raise LLMServiceError(
            "The AI provider returned incomplete PDF asset classifications."
        )

    return classifications


async def _advisor_chat_events(
    request: AIChatRequest,
    current_user: User,
    advisor_service: AIAdvisorService,
    db: Session,
    *,
    stream_response: bool,
) -> AsyncIterator[dict[str, str | int]]:
    """Run one chat turn and emit events from a shared business workflow."""
    try:
        advisory_topic_instructions = build_advisory_topic_instructions(
            get_advisory_settings(db)["topics"]
        )
        memory_context = None
        conversation_context = None
        goal_conversation_context = None
        goal_planning_context = None
        goal_review_context = None
        goal_review = None
        confirmed_goal_plan = None
        confirmed_intent_memory: ExtractedMemory | None = None
        rule_context = None
        conversation = None
        last_assistant_message = None
        if request.goal_id is not None:
            goal_review = get_goal(
                db,
                current_user.id,
                request.goal_id,
            )
            if goal_review is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Goal was not found.",
                )
            goal_review_context = build_goal_review_context(goal_review)
        if request.conversation_id is not None:
            conversation = get_conversation(
                db, current_user.id, request.conversation_id
            )
            if conversation is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation was not found.",
                )
            conversation_context = build_conversation_context(
                conversation.messages
            )
            goal_conversation_context = build_goal_conversation_context(
                conversation.messages
            )
            if (
                conversation.messages
                and conversation.messages[-1].role == "assistant"
            ):
                last_assistant_message = conversation.messages[-1].content
        goal_discussion = (
            request.goal_id is None
            and _is_goal_planning_discussion(
                request.message,
                conversation_context,
            )
        )
        financial_snapshot = _financial_snapshot_for_user(
            db, current_user.id
        )
        financial_context = _financial_context_from_snapshot(
            financial_snapshot,
            include_empty=goal_discussion or goal_review is not None,
        )
        memory_lookup_message = request.message
        if goal_review is not None:
            memory_lookup_message = (
                f"{request.message}\n"
                f"Goal: {goal_review.name}. "
                f"Category: {goal_review.category}."
            )
        elif goal_discussion and goal_conversation_context is not None:
            memory_lookup_message = (
                f"{request.message}\n{goal_conversation_context}"
            )
        memory_context = build_memory_context(
            retrieve_relevant_memories(
                db,
                current_user.id,
                memory_lookup_message,
            )
        )
        if request.rule_id is not None:
            rule = get_financial_rule_by_id(db, request.rule_id)
            if rule is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Financial rule was not found.",
                )
            rule_context = _build_selected_rule_context(rule)

        if conversation is not None:
            stored_user_message = request.message
            if goal_review is not None:
                stored_user_message = build_goal_review_message(goal_review)
                if conversation.title == "New Conversation":
                    conversation.title = (
                        f"Goal review: {goal_review.name}"
                    )[:255]
            add_message(
                db,
                conversation,
                "user",
                stored_user_message,
            )

        reply_json = getattr(advisor_service, "reply_json", None)
        if goal_discussion:
            clarification = await _clarify_goal_intent(
                advisor_service,
                goal_conversation_context,
                last_assistant_message,
                request.message,
            )
            if (
                clarification.status
                == GoalIntentClarificationStatus.NEEDS_CLARIFICATION
                and clarification.clarifying_question is not None
            ):
                answer = clarification.clarifying_question
                if conversation is not None:
                    add_message(db, conversation, "assistant", answer)
                if stream_response:
                    yield {
                        "type": "delta",
                        "content": answer,
                    }
                yield {
                    "type": "done",
                    "answer": answer,
                    "model": advisor_service.model,
                }
                return
            if (
                clarification.status
                == GoalIntentClarificationStatus.RESOLVED
                and clarification.confirmed_fact is not None
                and clarification.memory_category is not None
            ):
                confirmed_intent_memory = ExtractedMemory(
                    fact=clarification.confirmed_fact,
                    category=clarification.memory_category,
                )
                remember_from_conversation_turn(
                    db,
                    current_user.id,
                    user_message="",
                    assistant_message="",
                    structured_memories=[confirmed_intent_memory],
                )
                memory_context = build_memory_context(
                    retrieve_relevant_memories(
                        db,
                        current_user.id,
                        clarification.confirmed_fact,
                    )
                )

            goal_state = None
            if reply_json is not None:
                goal_state = await _extract_goal_planning_state(
                    advisor_service,
                    goal_conversation_context,
                    request.message,
                    memory_context,
                    financial_context,
                )
            confirmed_goal_plan = _prepare_confirmed_goal_plan(
                goal_state,
                current_user.id,
                conversation.id if conversation is not None else None,
            )
            goal_planning_context = _build_goal_workflow_context(
                goal_state,
                financial_snapshot,
                confirmed_goals_available=confirmed_goal_plan is not None,
            )
        elif (
            request.goal_id is None
            and request.rule_id is None
            and reply_json is not None
        ):
            intent_payload = await reply_json(
                build_financial_rule_intent_prompt(
                    request.message,
                ),
                FINANCIAL_RULE_INTENT_RESPONSE_SCHEMA,
            )
            rule_intent = normalize_financial_rule_intent_payload(
                intent_payload,
            )
            rule_context = build_financial_rule_context_from_intent(
                db=db,
                intent=rule_intent,
            )

        message = _build_grounded_message(
            user_message=request.message,
            memory_context=memory_context,
            conversation_context=conversation_context,
            financial_context=financial_context,
            goal_planning_context=goal_planning_context,
            rule_context=rule_context,
            goal_review_context=goal_review_context,
        )
        if stream_response:
            answer_parts: list[str] = []
            async for chunk in advisor_service.stream_reply(
                message,
                system_instruction=advisory_topic_instructions,
            ):
                answer_parts.append(chunk)
                yield {
                    "type": "delta",
                    "content": chunk,
                }
            answer = _formatted_answer("".join(answer_parts))
        else:
            answer = _formatted_answer(
                await advisor_service.reply(
                    message,
                    system_instruction=advisory_topic_instructions,
                )
            )

        if confirmed_goal_plan is not None and conversation is not None:
            save_confirmed_goal_plan(
                db,
                conversation.id,
                confirmed_goal_plan.fingerprint,
                confirmed_goal_plan.goals,
            )

        if conversation is not None:
            add_message(db, conversation, "assistant", answer)

        try:
            memory_snapshot = get_memory_snapshot(
                db,
                current_user.id,
                "\n".join(
                    context
                    for context in (
                        conversation_context,
                        request.message,
                        answer,
                    )
                    if context
                ),
            )
            structured_memories = []
            if reply_json is not None:
                try:
                    memory_payload = await reply_json(
                        build_memory_extraction_prompt(
                            memory_snapshot,
                            conversation_context,
                            request.message,
                            answer,
                        ),
                        MEMORY_EXTRACTION_RESPONSE_SCHEMA,
                    )
                    structured_memories = normalize_memory_extraction_payload(
                        memory_payload,
                        memory_snapshot,
                    )
                except (
                    LLMConfigurationError,
                    LLMRateLimitError,
                    LLMServiceError,
                ):
                    structured_memories = []
            if confirmed_intent_memory is not None:
                structured_memories.append(confirmed_intent_memory)

            remember_from_conversation_turn(
                db,
                current_user.id,
                user_message=(
                    ""
                    if confirmed_intent_memory is not None
                    else request.message
                ),
                assistant_message=answer,
                conversation_context=conversation_context,
                structured_memories=structured_memories,
            )
        except Exception:
            db.rollback()
            logger.exception(
                "Unable to update memory after a completed chat response."
            )

        yield {
            "type": "done",
            "answer": answer,
            "model": advisor_service.model,
        }
    except (
        LLMConfigurationError,
        LLMRateLimitError,
        LLMServiceError,
    ) as error:
        _raise_llm_http_error(error)


@router.post(
    "/chat",
    response_model=AIChatResponse,
)
async def chat_with_advisor(
    request: AIChatRequest,
    current_user: User = Depends(get_current_user),
    advisor_service: AIAdvisorService = Depends(
        get_ai_advisor_service
    ),
    db: Session = Depends(get_db),
):
    """Return an educational reply from the configured LLM."""
    async for event in _advisor_chat_events(
        request,
        current_user,
        advisor_service,
        db,
        stream_response=False,
    ):
        if event["type"] == "done":
            return AIChatResponse(
                answer=str(event["answer"]),
                model=str(event["model"]),
            )

    _raise_llm_http_error(
        LLMServiceError("The AI service returned no response.")
    )


async def _stream_advisor_chat(
    request: AIChatRequest,
    current_user: User,
    advisor_service: AIAdvisorService,
    db: Session,
) -> AsyncIterator[str]:
    try:
        async for event in _advisor_chat_events(
            request,
            current_user,
            advisor_service,
            db,
            stream_response=True,
        ):
            yield json.dumps(event, ensure_ascii=False) + "\n"
    except HTTPException as error:
        yield json.dumps(
            {
                "type": "error",
                "message": str(error.detail),
                "status": error.status_code,
            },
            ensure_ascii=False,
        ) + "\n"
    except Exception:
        logger.exception("Unexpected advisor streaming failure.")
        yield json.dumps(
            {
                "type": "error",
                "message": (
                    "Unable to stream the AI response. Please try again."
                ),
                "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
            },
            ensure_ascii=False,
        ) + "\n"


@router.post("/chat/stream")
async def stream_chat_with_advisor(
    request: AIChatRequest,
    current_user: User = Depends(get_current_user),
    advisor_service: AIAdvisorService = Depends(
        get_ai_advisor_service
    ),
    db: Session = Depends(get_db),
):
    """Stream an educational LLM reply as newline-delimited JSON events."""
    return StreamingResponse(
        _stream_advisor_chat(
            request,
            current_user,
            advisor_service,
            db,
        ),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/chat/pdf",
    response_model=AIPdfChatResponse,
)
async def chat_with_pdf_upload(
    message: str = Form(default=""),
    conversation_id: int | None = Form(default=None),
    files: list[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
    advisor_service: AIAdvisorService = Depends(
        get_ai_advisor_service
    ),
    db: Session = Depends(get_db),
):
    """Classify uploaded PDF assets and update HomePage financial data."""

    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload at least one PDF file.",
        )

    conversation = None
    conversation_context = None
    goal_conversation_context = None
    if conversation_id is not None:
        conversation = get_conversation(
            db,
            current_user.id,
            conversation_id,
        )
        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation was not found.",
            )
        conversation_context = build_conversation_context(
            conversation.messages
        )
        goal_conversation_context = build_goal_conversation_context(
            conversation.messages
        )

    results = []
    for file in files:
        content = await file.read()
        _validate_pdf_upload(file, content)
        try:
            results.append(
                await process_financial_pdf(
                    db,
                    current_user.id,
                    filename=file.filename or "uploaded.pdf",
                    content=content,
                    classify_ambiguous_transactions=(
                        lambda candidates: _classify_pdf_transactions(
                            advisor_service,
                            candidates,
                        )
                    ),
                    classify_cash_flow_kinds=(
                        lambda candidates: _classify_pdf_cash_flow_kinds(
                            advisor_service,
                            candidates,
                        )
                    ),
                    classify_asset_candidates=(
                        lambda candidates: _classify_pdf_assets(
                            advisor_service,
                            candidates,
                        )
                    ),
                )
            )
        except PdfExtractionError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(error),
            ) from error
        except (
            LLMConfigurationError,
            LLMRateLimitError,
            LLMServiceError,
        ) as error:
            _raise_llm_http_error(error)

    user_message = (
        message.strip()
        or "Extract financial information from the uploaded PDF."
    )
    filenames = ", ".join(
        result.filename
        for result in results
    )

    if conversation is not None:
        add_message(
            db,
            conversation,
            "user",
            (
                f"Uploaded PDF(s): {filenames}\n"
                f"Request: {user_message}"
            ),
        )

    pdf_context = build_pdf_ai_context(
        user_message=user_message,
        results=results,
    )
    memory_context = build_memory_context(
        retrieve_relevant_memories(
            db,
            current_user.id,
            user_message,
        )
    )
    goal_discussion = _is_goal_planning_discussion(
        user_message,
        conversation_context,
    )
    financial_snapshot = _financial_snapshot_for_user(
        db, current_user.id
    )
    financial_context = _financial_context_from_snapshot(
        financial_snapshot,
        include_empty=goal_discussion,
    )
    goal_planning_context = None
    confirmed_goal_plan = None
    try:
        if goal_discussion:
            goal_state = await _extract_goal_planning_state(
                advisor_service,
                goal_conversation_context,
                user_message,
                memory_context,
                financial_context,
            )
            confirmed_goal_plan = _prepare_confirmed_goal_plan(
                goal_state,
                current_user.id,
                conversation.id if conversation is not None else None,
            )
            goal_planning_context = _build_goal_workflow_context(
                goal_state,
                financial_snapshot,
                confirmed_goals_available=confirmed_goal_plan is not None,
            )
        context = _build_grounded_message(
            user_message=pdf_context,
            memory_context=memory_context,
            conversation_context=conversation_context,
            financial_context=financial_context,
            goal_planning_context=goal_planning_context,
            rule_context=None,
        )
        answer = _formatted_answer(
            await advisor_service.reply(context)
        )
        if confirmed_goal_plan is not None and conversation is not None:
            save_confirmed_goal_plan(
                db,
                conversation.id,
                confirmed_goal_plan.fingerprint,
                confirmed_goal_plan.goals,
            )
    except (
        LLMConfigurationError,
        LLMRateLimitError,
        LLMServiceError,
    ) as error:
        _raise_llm_http_error(error)

    if conversation is not None:
        add_message(
            db,
            conversation,
            "assistant",
            answer,
        )

    imported_records = [
        record
        for result in results
        for record in result.imported_records
    ]
    fallback_reason = "; ".join(
        result.fallback_reason
        for result in results
        if result.fallback_reason
    ) or None

    return AIPdfChatResponse(
        answer=answer,
        model=advisor_service.model or PDF_MODEL_CONTEXT,
        low_confidence=any(result.low_confidence for result in results),
        extracted_text_characters=sum(
            len(result.extracted_text)
            for result in results
        ),
        imported_records=imported_records_to_api(imported_records),
        fallback_reason=fallback_reason,
    )
