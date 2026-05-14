import fs from "fs";
import {
  Connection,
  Keypair,
  PublicKey,
  SystemProgram,
  Transaction,
  sendAndConfirmTransaction,
  SendTransactionError,
} from "@solana/web3.js";

import {
  PROGRAM_ID as MPL_TOKEN_METADATA_PROGRAM_ID,
  createCreateMetadataAccountV3Instruction,
} from "@metaplex-foundation/mpl-token-metadata";

const RPC = process.env.RPC ?? "https://api.mainnet-beta.solana.com";
const TREASURY_KEYPAIR = process.env.TREASURY_KEYPAIR ?? "";
const MINT = process.env.MINT ?? "";
const URI = process.env.URI ?? "";

if (!TREASURY_KEYPAIR) throw new Error("Set TREASURY_KEYPAIR=/path/to/keypair.json");
if (!MINT) throw new Error('Set MINT="...mint pubkey..."');
if (!URI) throw new Error("Set URI=https://.../gip.metadata.json");

function loadKeypair(path: string): Keypair {
  const raw = JSON.parse(fs.readFileSync(path, "utf8"));
  return Keypair.fromSecretKey(Uint8Array.from(raw));
}

async function main() {
  const c = new Connection(RPC, "confirmed");
  const treasury = loadKeypair(TREASURY_KEYPAIR);
  const mintPk = new PublicKey(MINT);

  const [metadataPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("metadata"), MPL_TOKEN_METADATA_PROGRAM_ID.toBuffer(), mintPk.toBuffer()],
    MPL_TOKEN_METADATA_PROGRAM_ID
  );

  console.log("mint:", mintPk.toBase58());
  console.log("metadata_pda:", metadataPda.toBase58());
  console.log("updateAuthority:", treasury.publicKey.toBase58());

  // Standard fungible token metadata (NOT pNFT)
  const name = "Glyph Internet Protocol";
  const symbol = "GIP";

  const ix = createCreateMetadataAccountV3Instruction(
    {
      metadata: metadataPda,
      mint: mintPk,
      mintAuthority: treasury.publicKey,
      payer: treasury.publicKey,
      updateAuthority: treasury.publicKey,
      systemProgram: SystemProgram.programId,
    },
    {
      createMetadataAccountArgsV3: {
        data: {
          name,
          symbol,
          uri: URI,
          sellerFeeBasisPoints: 0,
          creators: null,
          collection: null,
          uses: null,
        },
        isMutable: true, // you can later update URI if you want
        collectionDetails: null,
      },
    }
  );

  const tx = new Transaction().add(ix);

  try {
    const sig = await sendAndConfirmTransaction(c, tx, [treasury], {
      commitment: "confirmed",
    });
    console.log("TX:", sig);
    console.log("OK: metaplex metadata created");
  } catch (e: any) {
    console.error("FAILED:", e?.message || e);
    if (e instanceof SendTransactionError) {
      const logs = await e.getLogs(c);
      console.log("FULL LOGS:\n" + (logs || []).join("\n"));
    } else if (e?.transactionLogs) {
      console.log("transactionLogs:\n" + e.transactionLogs.join("\n"));
    }
    process.exit(1);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});