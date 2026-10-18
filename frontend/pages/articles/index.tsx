import Head from "next/head";
import Image from "next/image";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import ArticlesFooter from "@/components/articles/ArticlesFooter";
import { formatArticleDate, getArticles } from "@/content/articles";

const articles = getArticles();

export default function ArticlesIndexPage() {
  return (
    <>
      <Head>
        <title>Articles & releases — Tessaris</title>
        <meta name="description" content="Product updates, research results and announcements from Tessaris." />
        <link rel="canonical" href="https://tessaris.ai/articles" />
      </Head>

      <div className="tessaris-publications h-[calc(100vh-72px)] overflow-y-auto overflow-x-hidden bg-white text-[#071329]">
        <main>
          <header className="border-b border-slate-200 bg-[#f7faff] px-5 py-16 sm:px-8 sm:py-24">
            <div className="mx-auto max-w-[1120px]">
              <div className="text-[11px] font-black uppercase tracking-[.2em] text-[#1748e5]">Tessaris publications</div>
              <h1 className="mt-5 max-w-4xl text-balance text-5xl font-black leading-[.98] tracking-[-.05em] sm:text-7xl">
                Articles &amp; releases.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600 sm:text-xl">
                What we are building, testing and learning as Tessaris develops owner-controlled business intelligence.
              </p>
            </div>
          </header>

          <section className="px-5 py-14 sm:px-8 sm:py-20">
            <div className="mx-auto max-w-[1120px]">
              <div className="border-b border-slate-200 pb-4 text-xs font-black uppercase tracking-[.18em] text-slate-500">Latest</div>
              <div>
                {articles.map((article, index) => {
                  const image = article.hero.kind === "image" ? article.hero : null;
                  return (
                    <article key={article.slug} className="grid gap-7 border-b border-slate-200 py-10 md:grid-cols-[1fr_280px] md:items-center lg:grid-cols-[1fr_360px]">
                      <div className="max-w-3xl">
                        <div className="flex flex-wrap items-center gap-2 text-xs font-bold text-slate-500">
                          <span className="text-[#1748e5]">{article.category}</span>
                          <span aria-hidden="true">·</span>
                          <time dateTime={article.publishedAt}>{formatArticleDate(article.publishedAt)}</time>
                          <span aria-hidden="true">·</span>
                          <span>{article.readMinutes} min read</span>
                        </div>
                        <h2 className="mt-4 text-balance text-3xl font-black leading-[1.06] tracking-[-.035em] sm:text-4xl">
                          <Link href={`/articles/${article.slug}`} className="!border-0 !bg-transparent !p-0 !text-[#071329] hover:!text-[#1748e5]">
                            {article.title}
                          </Link>
                        </h2>
                        <p className="mt-4 max-w-2xl text-base leading-7 text-slate-600">{article.excerpt}</p>
                        <Link href={`/articles/${article.slug}`} className="mt-6 inline-flex items-center gap-2 !border-0 !bg-transparent !p-0 text-sm font-extrabold !text-[#1748e5]">
                          Read article <ArrowRight size={16} aria-hidden="true" />
                        </Link>
                      </div>
                      {image ? (
                        <Link href={`/articles/${article.slug}`} aria-label={`Read ${article.title}`} className="relative aspect-[16/9] overflow-hidden rounded-2xl !border-0 !bg-[#eef3f9] !p-0">
                          <Image src={image.src} alt={image.alt} fill priority={index === 0} sizes="(max-width: 768px) 100vw, 360px" className="border-0 object-cover" />
                        </Link>
                      ) : article.hero.kind === "video" ? (
                        <video muted playsInline preload="metadata" poster={article.hero.poster} className="aspect-video w-full rounded-2xl bg-[#071329] object-cover">
                          <source src={article.hero.src} />
                        </video>
                      ) : null}
                    </article>
                  );
                })}
              </div>
            </div>
          </section>
        </main>
        <ArticlesFooter />
      </div>
    </>
  );
}
