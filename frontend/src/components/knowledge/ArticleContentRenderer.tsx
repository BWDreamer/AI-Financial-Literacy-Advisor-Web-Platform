import { useEffect } from "react";
import Image from "@tiptap/extension-image";
import TextAlign from "@tiptap/extension-text-align";
import Underline from "@tiptap/extension-underline";
import { EditorContent, JSONContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import type { ArticleContentBlock, ArticleContentBlocks } from "../../api/articles";
import { resolveImageUrl } from "../../utils/imageUrl";
import { RichTextBlockStyle } from "./richTextExtensions";

type RendererProps = {
  contentBlocks: ArticleContentBlocks;
};

function normalizeImageNode(node: JSONContent): JSONContent {
  const attrs = node.attrs ? { ...node.attrs } : undefined;

  if (node.type === "image" && typeof attrs?.src === "string") {
    attrs.src = resolveImageUrl(attrs.src) ?? attrs.src;
  }

  return {
    ...node,
    ...(attrs ? { attrs } : {}),
    ...(node.content ? { content: node.content.map(normalizeImageNode) } : {}),
  };
}

function legacyBlockToTipTapNode(block: ArticleContentBlock): JSONContent {
  if (block.type === "image") {
    const src = typeof block.src === "string" ? block.src : block.attrs?.src;
    const alt = typeof block.alt === "string" ? block.alt : block.attrs?.alt;
    const caption = typeof block.caption === "string" ? block.caption : block.attrs?.title;

    return {
      type: "image",
      attrs: {
        src: typeof src === "string" ? resolveImageUrl(src) ?? src : "",
        alt: typeof alt === "string" ? alt : "",
        title: typeof caption === "string" ? caption : null,
      },
    };
  }

  if (block.content || block.attrs || block.marks || block.type === "heading" || block.type.includes("List")) {
    return normalizeImageNode({
      ...block,
      content: block.content?.map(legacyBlockToTipTapNode),
    } as JSONContent);
  }

  if (block.type === "paragraph") {
    return {
      type: "paragraph",
      content: block.text ? [{ type: "text", text: block.text, marks: block.marks }] : [],
      attrs: block.attrs,
    };
  }

  return normalizeImageNode(block as JSONContent);
}

function toTipTapDoc(contentBlocks: ArticleContentBlocks): JSONContent {
  if (!Array.isArray(contentBlocks) && contentBlocks.type === "doc") {
    return normalizeImageNode(contentBlocks as JSONContent);
  }

  const content = Array.isArray(contentBlocks)
    ? contentBlocks.map(legacyBlockToTipTapNode)
    : [legacyBlockToTipTapNode(contentBlocks)];

  return {
    type: "doc",
    content: content.length ? content : [{ type: "paragraph" }],
  };
}

export default function ArticleContentRenderer({ contentBlocks }: RendererProps) {
  const content = toTipTapDoc(contentBlocks);
  const editor = useEditor({
    editable: false,
    extensions: [
      StarterKit,
      Underline,
      RichTextBlockStyle,
      Image.configure({ inline: false, allowBase64: false }),
      TextAlign.configure({ types: ["heading", "paragraph"] }),
    ],
    content,
    editorProps: {
      attributes: {
        class: "article-content mx-auto max-w-3xl text-base leading-8 text-slate-700 outline-none [&_a]:text-blue-600 [&_a]:underline [&_blockquote]:border-l-4 [&_blockquote]:border-slate-200 [&_blockquote]:pl-4 [&_blockquote]:italic [&_h1]:text-3xl [&_h1]:font-bold [&_h1]:leading-tight [&_h2]:text-2xl [&_h2]:font-bold [&_h3]:text-xl [&_h3]:font-bold [&_img]:mx-auto [&_img]:my-8 [&_img]:h-56 [&_img]:w-full [&_img]:max-w-xl [&_img]:rounded-2xl [&_img]:object-cover sm:[&_img]:h-64 [&_ol]:list-decimal [&_ol]:pl-6 [&_p]:my-5 [&_strong]:font-bold [&_ul]:list-disc [&_ul]:pl-6",
      },
    },
  });

  useEffect(() => {
    editor?.commands.setContent(toTipTapDoc(contentBlocks));
  }, [contentBlocks, editor]);

  if (!editor) return <p>No article content is available yet.</p>;
  return <EditorContent editor={editor} />;
}
