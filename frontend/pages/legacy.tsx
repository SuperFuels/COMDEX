import type { GetServerSideProps } from "next";

export default function LegacyTessarisSite() {
  return null;
}

export const getServerSideProps: GetServerSideProps = async () => ({
  redirect: {
    destination: "/glyph",
    permanent: false,
  },
});
