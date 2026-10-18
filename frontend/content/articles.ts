export type ArticleMedia =
  | {
      kind: "image";
      src: string;
      alt: string;
      caption?: string;
    }
  | {
      kind: "video";
      src: string;
      poster?: string;
      caption?: string;
    };

export type ArticleBlock =
  | { type: "paragraph"; content: string }
  | { type: "heading"; content: string }
  | { type: "list"; items: string[] }
  | { type: "pullquote"; content: string }
  | { type: "media"; media: ArticleMedia };

export type Article = {
  slug: string;
  title: string;
  excerpt: string;
  category: "Article" | "Research" | "Press release";
  publishedAt: string;
  author: string;
  readMinutes: number;
  hero: ArticleMedia;
  blocks: ArticleBlock[];
};

export const articles: Article[] = [
  {
    slug: "30b-model-on-an-sd-card",
    title: "We put a 30-billion-parameter AI model on an SD card—and made it run 4.48× faster on a standard Mac.",
    excerpt:
      "Tessaris reduced Qwen3-30B-A3B by 40.13%, retained 97.85% of its normalised task score and passed all 208 production checks.",
    category: "Research",
    publishedAt: "2026-10-18",
    author: "Tessaris Research",
    readMinutes: 4,
    hero: {
      kind: "image",
      src: "/articles/tessaris-sd-model-rack.png",
      alt: "A Tessaris portable model library with ten specialist AI model cards in a silver local storage rack",
    },
    blocks: [
      {
        type: "paragraph",
        content: "We’ve reached an important milestone in the development of Tessaris and AION.",
      },
      {
        type: "paragraph",
        content:
          "Starting with Qwen3-30B-A3B, we reduced the model from 18.56 GB to 11.11 GB—a 40.13% reduction in storage.",
      },
      {
        type: "paragraph",
        content:
          "But making a model smaller means very little if it becomes slow, unreliable or noticeably less capable. So we tested it against the original model.",
      },
      {
        type: "list",
        items: [
          "4.48× faster in matched CPU testing",
          "97.85% of the original normalised task score retained",
          "91/100 versus 93/100 across our business benchmark",
          "208/208 Tessaris production checks passed",
          "Successfully runs with 20 GPU layers on an 18 GB Mac",
        ],
      },
      {
        type: "paragraph",
        content:
          "The original model could not reliably use either 10 or 20 GPU layers on the same machine because it exhausted the available memory.",
      },
      {
        type: "heading",
        content: "Why portable local intelligence matters",
      },
      {
        type: "paragraph",
        content:
          "AION is being designed to operate with a portable library of specialist models stored on an SD-card rack.",
      },
      {
        type: "paragraph",
        content:
          "Instead of requiring every business to depend entirely on expensive cloud infrastructure, Tessaris can select and run the appropriate local model for the work—on ordinary hardware, close to the company’s own data.",
      },
      {
        type: "paragraph",
        content:
          "Our approach selectively reduces the model while protecting the components that matter most. Tessaris then adds structured validation and deterministic controls around the model’s output. We’re not publishing the complete method yet, but the result can be seen and tested working inside the Tessaris operating system.",
      },
      {
        type: "heading",
        content: "What this result does—and does not—prove",
      },
      {
        type: "paragraph",
        content:
          "We are not claiming universal, lossless intelligence from one benchmark. This was a controlled 100-case business test, and the compressed model finished two percentage points behind the original after normalisation.",
      },
      {
        type: "pullquote",
        content:
          "A 30B-class model, 40.13% smaller, running 4.48× faster on a standard Mac, while the complete Tessaris system passes every production check.",
      },
      {
        type: "paragraph",
        content:
          "That changes what becomes possible for private, portable and locally operated business AI.",
      },
      {
        type: "paragraph",
        content: "And this is only the first model.",
      },
    ],
  },
];

export function getArticles(): Article[] {
  return [...articles].sort(
    (left, right) => new Date(right.publishedAt).getTime() - new Date(left.publishedAt).getTime(),
  );
}

export function getArticle(slug: string): Article | undefined {
  return articles.find((article) => article.slug === slug);
}

export function formatArticleDate(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}
