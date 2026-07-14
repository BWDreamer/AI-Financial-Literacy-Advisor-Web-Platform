import type { CSSProperties, ReactNode } from "react";
import type { ArticleContentBlock, ArticleContentMark } from "../../api/articles";
import { resolveImageUrl } from "../../utils/imageUrl";

type RendererProps = {
  contentBlocks: ArticleContentBlock[];
};

function isSafeLink(value: unknown): value is string {
  if (typeof value !== "string") return false;
  return /^(https?:|mailto:|tel:|\/)/i.test(value);
}

function safeTextAlign(value: unknown): CSSProperties | undefined {
  if (value === "left" || value === "center" || value === "right" || value === "justify") {
    return { textAlign: value };
  }

  return undefined;
}

function safeFontStyle(attrs: Record<string, unknown> | undefined): CSSProperties | undefined {
  if (!attrs) return undefined;

  const style: CSSProperties = {};

  if (typeof attrs.fontSize === "string" && /^\d{1,2}(px|rem|em)$/.test(attrs.fontSize)) {
    style.fontSize = attrs.fontSize;
  }

  if (typeof attrs.color === "string" && /^#[0-9a-f]{3,8}$/i.test(attrs.color)) {
    style.color = attrs.color;
  }

  return Object.keys(style).length ? style : undefined;
}

function renderMarkedText(text: string, marks: ArticleContentMark[] = []) {
  return marks.reduce<ReactNode>((content, mark) => {
    if (mark.type === "bold") return <strong>{content}</strong>;
    if (mark.type === "italic") return <em>{content}</em>;
    if (mark.type === "underline") return <u>{content}</u>;

    if (mark.type === "link") {
      const href = mark.attrs?.href;
      if (!isSafeLink(href)) return content;

      return <a href={href} target="_blank" rel="noreferrer">{content}</a>;
    }

    if (mark.type === "textStyle") {
      const style = safeFontStyle(mark.attrs);
      return style ? <span style={style}>{content}</span> : content;
    }

    return content;
  }, text);
}

function renderChildren(block: ArticleContentBlock, keyPrefix: string) {
  return block.content?.map((child, index) => renderBlock(child, `${keyPrefix}-${index}`)) ?? null;
}

function renderImage(block: ArticleContentBlock, key: string) {
  const srcValue = typeof block.src === "string" ? block.src : block.attrs?.src;
  const src = typeof srcValue === "string" ? resolveImageUrl(srcValue) : null;
  const altValue = typeof block.alt === "string" ? block.alt : block.attrs?.alt;
  const captionValue = typeof block.caption === "string" ? block.caption : block.attrs?.title;

  if (!src) return null;

  return (
    <figure key={key} className="my-8">
      <img src={src} alt={typeof altValue === "string" ? altValue : ""} />
      {typeof captionValue === "string" && captionValue && <figcaption>{captionValue}</figcaption>}
    </figure>
  );
}

function renderHeading(block: ArticleContentBlock, key: string) {
  const level = block.attrs?.level === 1 || block.attrs?.level === 2 || block.attrs?.level === 3
    ? block.attrs.level
    : 2;
  const style = safeTextAlign(block.attrs?.textAlign);

  if (level === 1) return <h1 key={key} style={style}>{renderChildren(block, key)}</h1>;
  if (level === 3) return <h3 key={key} style={style}>{renderChildren(block, key)}</h3>;
  return <h2 key={key} style={style}>{renderChildren(block, key)}</h2>;
}

function renderBlock(block: ArticleContentBlock, key: string): ReactNode {
  if (block.type === "text") {
    return renderMarkedText(block.text ?? "", block.marks);
  }

  if (block.type === "image") {
    return renderImage(block, key);
  }

  if (block.type === "heading") {
    return renderHeading(block, key);
  }

  if (block.type === "paragraph") {
    const style = safeTextAlign(block.attrs?.textAlign);
    const legacyText = block.text ? renderMarkedText(block.text, block.marks) : null;
    return <p key={key} style={style}>{renderChildren(block, key) ?? legacyText}</p>;
  }

  if (block.type === "bulletList") {
    return <ul key={key}>{renderChildren(block, key)}</ul>;
  }

  if (block.type === "orderedList") {
    return <ol key={key}>{renderChildren(block, key)}</ol>;
  }

  if (block.type === "listItem") {
    return <li key={key}>{renderChildren(block, key)}</li>;
  }

  if (block.type === "blockquote") {
    return <blockquote key={key}>{renderChildren(block, key)}</blockquote>;
  }

  if (block.type === "hardBreak") {
    return <br key={key} />;
  }

  return block.content?.length
    ? <div key={key}>{renderChildren(block, key)}</div>
    : null;
}

export default function ArticleContentRenderer({ contentBlocks }: RendererProps) {
  if (!contentBlocks.length) {
    return <p>No article content is available yet.</p>;
  }

  return (
    <div className="article-content mx-auto max-w-3xl text-base leading-8 text-slate-700">
      {contentBlocks.map((block, index) => renderBlock(block, `article-block-${index}`))}
    </div>
  );
}
