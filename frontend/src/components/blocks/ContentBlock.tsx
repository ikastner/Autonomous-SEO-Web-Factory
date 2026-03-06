import { ContentBlockSchema } from "@/types/schema";
import ReactMarkdown from "react-markdown";

export default function ContentBlock({
  heading,
  body_markdown,
  image_url,
  image_alt,
  image_position,
}: ContentBlockSchema) {
  const hasImage = image_url && image_position !== "none";
  const isImageLeft = image_position === "left";

  if (!hasImage) {
    return (
      <section className="py-20 px-6">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6">
            {heading}
          </h2>
          <div className="prose prose-lg max-w-none text-gray-700">
            <ReactMarkdown>{body_markdown}</ReactMarkdown>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="py-20 px-6">
      <div className="max-w-6xl mx-auto">
        <div
          className={`grid grid-cols-1 md:grid-cols-2 gap-12 items-center ${
            isImageLeft ? "md:flex-row-reverse" : ""
          }`}
        >
          <div className={isImageLeft ? "md:order-2" : ""}>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-6">
              {heading}
            </h2>
            <div className="prose prose-lg max-w-none text-gray-700">
              <ReactMarkdown>{body_markdown}</ReactMarkdown>
            </div>
          </div>
          <div className={isImageLeft ? "md:order-1" : ""}>
            <img
              src={image_url}
              alt={image_alt || ""}
              className="rounded-xl shadow-lg w-full h-auto"
            />
          </div>
        </div>
      </div>
    </section>
  );
}
