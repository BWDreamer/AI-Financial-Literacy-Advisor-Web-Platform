import { Extension } from "@tiptap/core";

export const fontSizeOptions = [
  { label: "Size", value: "" },
  { label: "15px", value: "0.95rem" },
  { label: "18px", value: "1.125rem" },
  { label: "22px", value: "1.35rem" },
  { label: "26px", value: "1.65rem" },
] as const;

export const spacingOptions = [
  { label: "Spacing", value: "" },
  { label: "Compact", value: "1.45" },
  { label: "Normal", value: "1.75" },
  { label: "Relaxed", value: "2" },
] as const;

export const RichTextBlockStyle = Extension.create({
  name: "richTextBlockStyle",

  addGlobalAttributes() {
    return [
      {
        types: ["paragraph", "heading"],
        attributes: {
          fontSize: {
            default: null,
            parseHTML: (element) => element.style.fontSize || null,
            renderHTML: (attributes) => (
              attributes.fontSize ? { style: `font-size: ${attributes.fontSize}` } : {}
            ),
          },
          lineHeight: {
            default: null,
            parseHTML: (element) => element.style.lineHeight || null,
            renderHTML: (attributes) => (
              attributes.lineHeight ? { style: `line-height: ${attributes.lineHeight}` } : {}
            ),
          },
        },
      },
    ];
  },
});
