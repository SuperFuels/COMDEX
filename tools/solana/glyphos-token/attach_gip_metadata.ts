import fs from "fs";
import { Connection, Keypair, PublicKey, Transaction } from "@solana/web3.js";
import { createCreateMetadataAccountV3Instruction } from "@metaplex-foundation/mpl-token-metadata";

// Metaplex Token Metadata program (fixed)
const TOKEN_METADATA_PROGRAM_ID = new PublicKey(
  "metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"
);

function loadKeypair(path: string): Keypair {
  const raw = JSON.parse(fs.readFileSync(path, "utf8"));
  return Keypair.fromSecretKey(Uint8Array.from(raw));
}

async function main() {
  const RPC = process.env.RPC ?? "https://api.mainnet-beta.solana.com";
  const TREASURY_KEYPAIR = process.env.TREASURY_KEYPAIR ?? "";
  const MINT = process.env.MINT ?? "";
  const URI = process.env.URI ?? "";

  if (!TREASURY_KEYPAIR) throw new Error("Set TREASURY_KEYPAIR");
  if (!MINT) throw new Error("Set MINT");
  if (!URI) throw new Error("Set URI");

  const connection = new Connection(RPC, "confirmed");
  const treasury = loadKeypair(TREASURY_KEYPAIR);
  const mint = new PublicKey(MINT);

  const [metadataPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("metadata"), TOKEN_METADATA_PROGRAM_ID.toBuffer(), mint.toBuffer()],
    TOKEN_METADATA_PROGRAM_ID
  );

  const ix = createCreateMetadataAccountV3Instruction(
    {
      metadata: metadataPda,
      mint,
      mintAuthority: treasury.publicKey,
      payer: treasury.publicKey,
      updateAuthority: treasury.publicKey,
    },
    {
      createMetadataAccountArgsV3: {
        data: {
          name: "Glyph Internet Protocol",
          symbol: "GIP",
          uri: URI,
          sellerFeeBasisPoints: 0,
          creators: null,
          collection: null,
          uses: null,
        },
        isMutable: true,
        collectionDetails: null,
      },
    }
  );

  const { blockhash } = await connection.getLatestBlockhash("confirmed");
  const tx = new Transaction().add(ix);
  tx.feePayer = treasury.publicKey;
  tx.recentBlockhash = blockhash;

  const sig = await connection.sendTransaction(tx, [treasury], { skipPreflight: false });
  await connection.confirmTransaction(sig, "confirmed");

  console.log("MINT:", mint.toBase58());
  console.log("METADATA_PDA:", metadataPda.toBase58());
  console.log("TX:", sig);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});