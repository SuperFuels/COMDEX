// frontend/pages/_document.tsx
import Document, { Html, Head, Main, NextScript, DocumentContext } from "next/document";

export default class MyDocument extends Document {
  static async getInitialProps(ctx: DocumentContext) {
    const initialProps = await Document.getInitialProps(ctx);
    return { ...initialProps };
  }

  render() {
    return (
      <Html lang="en">
        <Head>{/* fonts / meta can go here */}</Head>
        <body>
          <Main />
          <NextScript />
        </body>
      </Html>
    );
  }
}