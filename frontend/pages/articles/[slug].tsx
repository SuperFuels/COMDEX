import Head from "next/head";
import Link from "next/link";
import type { GetStaticPaths, GetStaticProps, InferGetStaticPropsType } from "next";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import ArticleMedia from "@/components/articles/ArticleMedia";
import ArticlesFooter from "@/components/articles/ArticlesFooter";
import { articles, formatArticleDate, getArticle, type Article } from "@/content/articles";

type ArticlePageProps = { article: Article };

export const getStaticPaths: GetStaticPaths = async () => ({
  paths: articles.map((article) => ({ params: { slug: article.slug } })),
  fallback: false,
});

export const getStaticProps: GetStaticProps<ArticlePageProps> = async ({ params }) => {
  const article = getArticle(String(params?.slug ?? ""));
  if (!article) return { notFound: true };
  return { props: { article } };
};

export default function ArticlePage({ article }: InferGetStaticPropsType<typeof getStaticProps>) {
  const canonicalUrl = `https://tessaris.ai/articles/${article.slug}`;
  const socialImage = article.hero.kind === "image" ? `https://tessaris.ai${article.hero.src}` : article.hero.poster;

  return (
    <>
      <Head>
        <title>{article.title} — Tessaris</title>
        <meta name="description" content={article.excerpt} />
        <link rel="canonical" href={canonicalUrl} />
        <meta property="og:type" content="article" />
        <meta property="og:title" content={article.title} />
        <meta property="og:description" content={article.excerpt} />
        <meta property="og:url" content={canonicalUrl} />
        {socialImage ? <meta property="og:image" content={socialImage} /> : null}
        <meta property="article:published_time" content={`${article.publishedAt}T00:00:00Z`} />
        <meta name="twitter:card" content="summary_large_image" />
      </Head>

      <div className="tessaris-publications h-[calc(100vh-72px)] overflow-y-auto overflow-x-hidden bg-white text-[#071329]">
        <main>
          <article>
            <header className="px-5 pb-10 pt-10 sm:px-8 sm:pb-14 sm:pt-16">
              <div className="mx-auto max-w-[920px]">
                <Link href="/articles" className="inline-flex items-center gap-2 !border-0 !bg-transparent !p-0 text-sm font-extrabold !text-[#1748e5]">
                  <ArrowLeft size={16} aria-hidden="true" /> All articles
                </Link>
                <div className="mt-12 flex flex-wrap items-center gap-2 text-xs font-bold text-slate-500">
                  <span className="text-[#1748e5]">{article.category}</span>
                  <span aria-hidden="true">·</span>
                  <time dateTime={article.publishedAt}>{formatArticleDate(article.publishedAt)}</time>
                  <span aria-hidden="true">·</span>
                  <span>{article.readMinutes} min read</span>
                </div>
                <h1 className="mt-5 text-balance text-4xl font-black leading-[1.02] tracking-[-.045em] sm:text-6xl lg:text-[68px]">{article.title}</h1>
                <p className="mt-7 max-w-3xl text-xl leading-8 text-slate-600">{article.excerpt}</p>
                <div className="mt-7 text-sm font-bold text-slate-500">By {article.author}</div>
              </div>
            </header>

            <div className="mx-auto max-w-[1160px] px-3 sm:px-8">
              <ArticleMedia media={article.hero} priority />
            </div>

            <div className="mx-auto max-w-[760px] px-5 py-14 sm:px-8 sm:py-20">
              {article.blocks.map((block, index) => {
                if (block.type === "heading") {
                  return <h2 key={index} className="mb-5 mt-14 text-balance text-3xl font-black leading-[1.08] tracking-[-.03em] sm:text-4xl">{block.content}</h2>;
                }
                if (block.type === "paragraph") {
                  return <p key={index} className="mb-7 text-lg leading-8 text-slate-700">{block.content}</p>;
                }
                if (block.type === "list") {
                  return (
                    <ul key={index} className="my-9 grid gap-3 rounded-[24px] border border-blue-100 bg-blue-50 p-6 sm:p-8">
                      {block.items.map((item) => (
                        <li key={item} className="flex gap-3 text-base font-bold leading-7 text-[#13274d]">
                          <span className="mt-1 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-[#1748e5] text-white"><Check size={12} strokeWidth={3} /></span>
                          {item}
                        </li>
                      ))}
                    </ul>
                  );
                }
                if (block.type === "pullquote") {
                  return (
                    <blockquote key={index} className="my-12 border-l-4 border-[#1748e5] py-2 pl-6 text-2xl font-black leading-[1.3] tracking-[-.02em] text-[#071329] sm:text-3xl">
                      {block.content}
                    </blockquote>
                  );
                }
                return <div key={index} className="my-12"><ArticleMedia media={block.media} /></div>;
              })}

              <div className="mt-16 rounded-[28px] bg-[#071329] p-7 text-white sm:p-10">
                <div className="text-[10px] font-black uppercase tracking-[.18em] text-blue-300">Follow the work</div>
                <h2 className="mt-4 text-3xl font-black tracking-[-.03em]">See what Tessaris is building next.</h2>
                <p className="mt-4 leading-7 text-slate-300">Explore the intelligence system behind Tessaris or join the waitlist for product access.</p>
                <div className="mt-7 flex flex-wrap gap-3">
                  <Link href="/aion" className="inline-flex items-center gap-2 rounded-full !border-0 !bg-white px-5 py-3 text-sm font-extrabold !text-[#071329]">Explore Si <ArrowRight size={16} /></Link>
                  <Link href="/waitlist" className="inline-flex items-center gap-2 rounded-full border border-white/25 !bg-transparent px-5 py-3 text-sm font-extrabold !text-white hover:!bg-white/10">Join the waitlist</Link>
                </div>
              </div>
            </div>
          </article>
        </main>
        <ArticlesFooter />
      </div>
    </>
  );
}
