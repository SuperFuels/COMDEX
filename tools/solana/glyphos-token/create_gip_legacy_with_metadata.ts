import fs from "fs";
import {
  Connection,
  Keypair,
  PublicKey,
  Transaction,
  sendAndConfirmTransaction,
} from "@solana/web3.js";

import {
  createMint,
  getOrCreateAssociatedTokenAccount,
  mintTo,
  setAuthority,
  AuthorityType,
  TOKEN_PROGRAM_ID,
} from "@solana/spl-token";

import {
  PROGRAM_ID as MPL_TOKEN_METADATA_PROGRAM_ID,
  createCreateMetadataAccountV3Instruction,
} from "@metaplex-foundation/mpl-token-metadata";

// ---- ENV / CONFIG ----
const RPC = process.env.RPC ?? "https://api.mainnet-beta.solana.com";
const TREASURY_KEYPAIR = process.env.TREASURY_KEYPAIR ?? "";
if (!TREASURY_KEYPAIR) throw new Error("Set TREASURY_KEYPAIR=/path/to/treasury.json");

const NAME = process.env.NAME ?? "Glyph Internet Protocol";
const SYMBOL = process.env.SYMBOL ?? "GIP";
const URI = process.env.URI ?? "";
if (!URI) throw new Error("Set URI=https://.../metadata.json (must be live 200 OK)");

const DECIMALS = Number(process.env.DECIMALS ?? "8");
const SUPPLY_TOKENS = BigInt(process.env.SUPPLY_TOKENS ?? "100000000000"); // 100Bn

const DEV_WALLET = process.env.DEV_WALLET ? new PublicKey(process.env.DEV_WALLET) : null;
const DEV_TOKENS = BigInt(process.env.DEV_TOKENS ?? "0"); // e.g. 7500000000

const MARKETING_WALLET = process.env.MARKETING_WALLET ? new PublicKey(process.env.MARKETING_WALLET) : null;
const MARKETING_TOKENS = BigInt(process.env.MARKETING_TOKENS ?? "0"); // e.g. 7500000000

// Metadata “lock”: make metadata immutable (most UIs treat this as “locked”)
const LOCK_METADATA = (process.env.LOCK_METADATA ?? "1") !== "0";

// 0 = no royalties (typical for meme token)
const SELLER_FEE_BPS = Number(process.env.SELLER_FEE_BPS ?? "0");

function loadKeypair(path: string): Keypair {
  const raw = JSON.parse(fs.readFileSync(path, "utf8"));
  return Keypair.fromSecretKey(Uint8Array.from(raw));
}

function mustOkAlloc(label: string, v: bigint) {
  if (v < 0n) throw new Error(`${label} must be >= 0`);
}

function findMetadataPda(mint: PublicKey) {
  return PublicKey.findProgramAddressSync(
    [
      Buffer.from("metadata"),
      MPL_TOKEN_METADATA_PROGRAM_ID.toBuffer(),
      mint.toBuffer(),
    ],
    MPL_TOKEN_METADATA_PROGRAM_ID
  )[0];
}

async function main() {
  const connection = new Connection(RPC, "confirmed");
  const treasury = loadKeypair(TREASURY_KEYPAIR);

  mustOkAlloc("DEV_TOKENS", DEV_TOKENS);
  mustOkAlloc("MARKETING_TOKENS", MARKETING_TOKENS);

  const allocTotal =
    (DEV_WALLET ? DEV_TOKENS : 0n) + (MARKETING_WALLET ? MARKETING_TOKENS : 0n);

  if (allocTotal > SUPPLY_TOKENS) {
    throw new Error("DEV_TOKENS + MARKETING_TOKENS exceeds total supply");
  }

  console.log("Treasury:", treasury.publicKey.toBase58());
  console.log("RPC:", RPC);

  // 1) Create legacy SPL mint (Tokenkeg)
  const mint = await createMint(
    connection,
    treasury,                 // payer
    treasury.publicKey,       // mint authority
    treasury.publicKey,       // freeze authority (we’ll revoke)
    DECIMALS,
    undefined,
    undefined,
    TOKEN_PROGRAM_ID
  );

  console.log("MINT (contract):", mint.toBase58());

  // 2) Create Metaplex metadata PDA
  const metadataPda = findMetadataPda(mint);

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
          name: NAME,
          symbol: SYMBOL,
          uri: URI,
          sellerFeeBasisPoints: SELLER_FEE_BPS,
          creators: null,
          collection: null,
          uses: null,
        },
        isMutable: !LOCK_METADATA ? true : false,
        collectionDetails: null,
      },
    }
  );

  const txMeta = new Transaction().add(ix);
  const sigMeta = await sendAndConfirmTransaction(connection, txMeta, [treasury], {
    commitment: "confirmed",
  });

  console.log("Metadata tx:", sigMeta);
  console.log("Metadata PDA:", metadataPda.toBase58());

  // 3) Mint allocations
  async function mintUiAmount(to: PublicKey, ui: bigint) {
    const ata = await getOrCreateAssociatedTokenAccount(
      connection,
      treasury,
      mint,
      to,
      false,
      "confirmed",
      undefined,
      TOKEN_PROGRAM_ID
    );
    await mintTo(
      connection,
      treasury,
      mint,
      ata.address,
      treasury.publicKey,
      ui, // spl-token accepts bigint ui amount? It expects raw amount; so convert below
      [],
      undefined,
      TOKEN_PROGRAM_ID
    );
    return ata.address;
  }

  // spl-token mintTo wants raw amount (base units)
  const base = 10n ** BigInt(DECIMALS);
  async function mintRaw(to: PublicKey, tokens: bigint) {
    const ata = await getOrCreateAssociatedTokenAccount(
      connection,
      treasury,
      mint,
      to,
      false,
      "confirmed",
      undefined,
      TOKEN_PROGRAM_ID
    );
    const sig = await mintTo(
      connection,
      treasury,
      mint,
      ata.address,
      treasury.publicKey,
      tokens * base,
      [],
      undefined,
      TOKEN_PROGRAM_ID
    );
    return { ata: ata.address, sig };
  }

  if (DEV_WALLET && DEV_TOKENS > 0n) {
    const r = await mintRaw(DEV_WALLET, DEV_TOKENS);
    console.log("Dev ATA:", r.ata.toBase58(), "tx:", r.sig);
  }

  if (MARKETING_WALLET && MARKETING_TOKENS > 0n) {
    const r = await mintRaw(MARKETING_WALLET, MARKETING_TOKENS);
    console.log("Marketing ATA:", r.ata.toBase58(), "tx:", r.sig);
  }

  const treasuryRemainder = SUPPLY_TOKENS - allocTotal;
  const tr = await mintRaw(treasury.publicKey, treasuryRemainder);
  console.log("Treasury ATA:", tr.ata.toBase58(), "tx:", tr.sig);

  // 4) Revoke authorities (fixed supply, no freeze)
  await setAuthority(
    connection,
    treasury,
    mint,
    treasury.publicKey,
    AuthorityType.MintTokens,
    null,
    [],
    undefined,
    TOKEN_PROGRAM_ID
  );

  await setAuthority(
    connection,
    treasury,
    mint,
    treasury.publicKey,
    AuthorityType.FreezeAccount,
    null,
    [],
    undefined,
    TOKEN_PROGRAM_ID
  );

  console.log("DONE ✅");
  console.log("PUBLIC CONTRACT (MINT):", mint.toBase58());
  console.log("URI:", URI);
  console.log("LOCK_METADATA:", LOCK_METADATA);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});