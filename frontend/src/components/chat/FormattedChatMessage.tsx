import { Fragment, type ReactNode } from "react";

type MessageBlock =
  | { type: "heading"; level: number; content: string }
  | { type: "paragraph"; content: string }
  | { type: "unordered-list"; items: string[] }
  | { type: "ordered-list"; items: string[] };

const HEADING_PATTERN = /^(#{1,4})\s+(.+)$/;
const UNORDERED_ITEM_PATTERN = /^[-*+]\s+(.+)$/;
const ORDERED_ITEM_PATTERN = /^\d+[.)]\s+(.+)$/;
const STRONG_PATTERN = /(\*\*[^*\n]+\*\*|__[^_\n]+__)/g;

function parseMessageBlocks(content: string): MessageBlock[] {
  const lines = content.split(/\r?\n/);
  const blocks: MessageBlock[] = [];
  let paragraphLines: string[] = [];

  function appendParagraph() {
    const paragraph = paragraphLines.join(" ").trim();
    if (paragraph) {
      blocks.push({ type: "paragraph", content: paragraph });
    }
    paragraphLines = [];
  }

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index].trim();
    if (!line) {
      appendParagraph();
      continue;
    }

    const heading = line.match(HEADING_PATTERN);
    if (heading) {
      appendParagraph();
      blocks.push({
        type: "heading",
        level: heading[1].length,
        content: heading[2],
      });
      continue;
    }

    const unorderedItem = line.match(UNORDERED_ITEM_PATTERN);
    if (unorderedItem) {
      appendParagraph();
      const items = [unorderedItem[1]];
      while (index + 1 < lines.length) {
        const nextItem = lines[index + 1].trim().match(UNORDERED_ITEM_PATTERN);
        if (!nextItem) break;
        items.push(nextItem[1]);
        index += 1;
      }
      blocks.push({ type: "unordered-list", items });
      continue;
    }

    const orderedItem = line.match(ORDERED_ITEM_PATTERN);
    if (orderedItem) {
      appendParagraph();
      const items = [orderedItem[1]];
      while (index + 1 < lines.length) {
        const nextItem = lines[index + 1].trim().match(ORDERED_ITEM_PATTERN);
        if (!nextItem) break;
        items.push(nextItem[1]);
        index += 1;
      }
      blocks.push({ type: "ordered-list", items });
      continue;
    }

    paragraphLines.push(line);
  }

  appendParagraph();
  return blocks;
}

function renderInlineContent(content: string): ReactNode[] {
  return content.split(STRONG_PATTERN).map((segment, index) => {
    const isStrong = (
      (segment.startsWith("**") && segment.endsWith("**"))
      || (segment.startsWith("__") && segment.endsWith("__"))
    );
    const key = `${index}-${segment}`;
    if (!isStrong) return <Fragment key={key}>{segment}</Fragment>;
    return <strong key={key} className="font-extrabold text-slate-950">{segment.slice(2, -2)}</strong>;
  });
}

function headingClassName(level: number) {
  if (level <= 2) return "text-xl font-extrabold leading-7 text-slate-950";
  if (level === 3) return "text-lg font-bold leading-7 text-slate-950";
  return "text-base font-bold leading-6 text-slate-950";
}

export default function FormattedChatMessage({ content }: { content: string }) {
  const blocks = parseMessageBlocks(content);

  return (
    <div className="space-y-3">
      {blocks.map((block, index) => {
        const key = `${block.type}-${index}`;
        if (block.type === "heading") {
          return (
            <h3 key={key} className={headingClassName(block.level)}>
              {renderInlineContent(block.content)}
            </h3>
          );
        }
        if (block.type === "unordered-list") {
          return (
            <ul key={key} className="list-disc space-y-1.5 pl-5 text-sm leading-6 text-slate-700">
              {block.items.map((item, itemIndex) => (
                <li key={`${itemIndex}-${item}`}>{renderInlineContent(item)}</li>
              ))}
            </ul>
          );
        }
        if (block.type === "ordered-list") {
          return (
            <ol key={key} className="list-decimal space-y-1.5 pl-5 text-sm leading-6 text-slate-700">
              {block.items.map((item, itemIndex) => (
                <li key={`${itemIndex}-${item}`}>{renderInlineContent(item)}</li>
              ))}
            </ol>
          );
        }
        return (
          <p key={key} className="text-sm leading-6 text-slate-700">
            {renderInlineContent(block.content)}
          </p>
        );
      })}
    </div>
  );
}
