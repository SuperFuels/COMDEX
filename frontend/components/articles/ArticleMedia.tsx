import Image from "next/image";
import type { ArticleMedia as ArticleMediaType } from "@/content/articles";

export default function ArticleMedia({ media, priority = false }: { media: ArticleMediaType; priority?: boolean }) {
  return (
    <figure>
      <div className="overflow-hidden rounded-[28px] border border-slate-200 bg-[#f4f7fb] shadow-[0_24px_70px_rgba(7,19,41,.09)]">
        {media.kind === "image" ? (
          <Image
            src={media.src}
            alt={media.alt}
            width={1814}
            height={867}
            priority={priority}
            sizes="(max-width: 1024px) 100vw, 1120px"
            className="block h-auto w-full border-0 object-cover"
          />
        ) : (
          <video
            controls
            playsInline
            preload="metadata"
            poster={media.poster}
            className="block aspect-video w-full bg-[#071329]"
          >
            <source src={media.src} />
            Your browser does not support embedded video.
          </video>
        )}
      </div>
      {media.caption ? <figcaption className="mt-3 text-sm leading-6 text-slate-500">{media.caption}</figcaption> : null}
    </figure>
  );
}
