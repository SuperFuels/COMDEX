import fs from "fs";
import { Connection, Keypair, PublicKey, Transaction, sendAndConfirmTransaction } from "@solana/web3.js";
import {
  PROGRAM_ID as TOKEN_METADATA_PROGRAM_ID,
  createCreateMetadataAccountV3Instruction,
} from "@metaplex-foundation/mpl-token-metadata";

const RPC = process.env.RPC ?? "https://api.mainnet-beta.solana.com";
const TREASURY_KEYPAIR = process.env.TREASURY_KEYPAIR ?? "";
const MINT = process.env.MINT ?? "";
const URI = process.env.URI ?? "";

if (!TREASURY_KEYPAIR) throw new Error("Set TREASURY_KEYPAIR=/path/to/keypair.json");
if (!MINT) throw new Error("Set MINT=<mint pubkey>");
if (!URI) throw new Error("Set URI=<https metadata json>");

function loadKeypair(path: string): Keypair {
  const raw = JSON.parse(fs.readFileSync(path, "utf8"));
  return Keypair.fromSecretKey(Uint8Array.from(raw));
}

async function main() {
  const connection = new Connection(RPC, "confirmed");
  const treasury = loadKeypair(TREASURY_KEYPAIR);
  const mint = new PublicKey(MINT);

  const [metadataPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("metadata"), TOKEN_METADATA_PROGRAM_ID.toBuffer(), mint.toBuffer()],
    TOKEN_METADATA_PROGRAM_ID
  );

  const data = {
    name: "Glyph Internet Protocol",
    symbol: "GIP",
    uri: URI,
    sellerFeeBasisPoints: 0,
    creators: null,     // keep simple for fungible tokens
    collection: null,
    uses: null,
  };

  const ix = createCreateMetadataAccountV3Instruction(
    {
      metadata: metadataPda,
      mint,
      mintAuthority: treasury.publicKey,
      payer: treasury.publicKey,
      updateAuthority: treasury.publicKey,
      systemProgram: new PublicKey("11111111111111111111111111111111"),
      rent: new PublicKey("SysvarRent111111111111111111111111111111111"),
    },
    {
      createMetadataAccountArgsV3: {
        data,
        isMutable: true,
        collectionDetails: null,
      },
    }
  );

  const tx = new Transaction().add(ix);
  const sig = await sendAndConfirmTransaction(connection, tx, [treasury], { commitment: "confirmed" });

  console.log("MINT:", mint.toBase58());
  console.log("METADATA_PDA:", metadataPda.toBase58());
  console.log("TX:", sig);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});