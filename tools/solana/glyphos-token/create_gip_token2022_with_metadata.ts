import fs from "fs";
import {
  Connection,
  Keypair,
  PublicKey,
  SystemProgram,
  Transaction,
  sendAndConfirmTransaction,
} from "@solana/web3.js";

import {
  TOKEN_2022_PROGRAM_ID,
  ExtensionType,
  getMintLen,
  createInitializeMintInstruction,
  createInitializeTransferFeeConfigInstruction,
  createAssociatedTokenAccountIdempotentInstruction,
  createMintToInstruction,
  AuthorityType,
  createSetAuthorityInstruction,
  getAssociatedTokenAddressSync,
  createInitializeMetadataPointerInstruction,
} from "@solana/spl-token";

import {
  pack,
  createInitializeInstruction as createInitializeTokenMetadataInstruction,
  createUpdateFieldInstruction,
  createUpdateAuthorityInstruction,
} from "@solana/spl-token-metadata";

// ---- ENV ----
const RPC = process.env.RPC ?? "https://api.mainnet-beta.solana.com";
const TREASURY_KEYPAIR = process.env.TREASURY_KEYPAIR ?? "";
if (!TREASURY_KEYPAIR) throw new Error("Set TREASURY_KEYPAIR to path of your treasury keypair json");

const DEV_WALLET = process.env.DEV_WALLET ? new PublicKey(process.env.DEV_WALLET) : null;
const DEV_TOKENS = process.env.DEV_TOKENS ? BigInt(process.env.DEV_TOKENS) : 0n;

const MARKETING_WALLET = process.env.MARKETING_WALLET ? new PublicKey(process.env.MARKETING_WALLET) : null;
const MARKETING_TOKENS = process.env.MARKETING_TOKENS ? BigInt(process.env.MARKETING_TOKENS) : 0n;

// Hosted JSON URI (must be LIVE 200 OK)
const METADATA_URI = process.env.URI ?? "";
if (!METADATA_URI) throw new Error("Set URI to your hosted metadata JSON (must be 200 OK)");

// ---- TOKEN PARAMS ----
const NAME = "Glyph Internet Protocol";
const SYMBOL = "GIP";
const DECIMALS = 8;                     // keep 8 for 100Bn to stay safely within u64
const SUPPLY_TOKENS = 100_000_000_000n; // 100Bn

// ---- TAX PARAMS ----
const FEE_BPS = 300;                 // 3%
const MAX_FEE_TOKENS = 100_000_000n; // cap per transfer

// If true: metadata update authority set to null after init (URI can still point to JSON you update)
const LOCK_METADATA_AUTHORITY = true;

const BASE = 10n ** BigInt(DECIMALS);
const MAX_FEE_BASE = MAX_FEE_TOKENS * BASE;

function loadKeypair(path: string): Keypair {
  const raw = JSON.parse(fs.readFileSync(path, "utf8"));
  return Keypair.fromSecretKey(Uint8Array.from(raw));
}

function mustNonNegative(x: bigint, label: string) {
  if (x < 0n) throw new Error(`${label} must be >= 0`);
}

async function main() {
  const connection = new Connection(RPC, "confirmed");
  const treasury = loadKeypair(TREASURY_KEYPAIR);

  mustNonNegative(DEV_TOKENS, "DEV_TOKENS");
  mustNonNegative(MARKETING_TOKENS, "MARKETING_TOKENS");

  const allocTotal =
    (DEV_WALLET ? DEV_TOKENS : 0n) + (MARKETING_WALLET ? MARKETING_TOKENS : 0n);

  if (allocTotal > SUPPLY_TOKENS) {
    throw new Error("DEV_TOKENS + MARKETING_TOKENS exceeds total supply");
  }

  // Authorities start as treasury, then we revoke what we don’t want.
  const mintAuthority = treasury.publicKey;
  const feeConfigAuthority = treasury.publicKey;         // will revoke
  const withdrawWithheldAuthority = treasury.publicKey;  // KEEP (collects tax)
  const freezeAuthority = treasury.publicKey;            // will revoke

  // Create mint with extensions:
  // - TransferFeeConfig (tax)
  // - MetadataPointer (points to metadata storage)
  // - TokenMetadata (variable length)
  const mintKeypair = Keypair.generate();
  const mint = mintKeypair.publicKey;

  const ADDITIONAL: Array<[string, string]> = [
    ["website", "https://www.tessaris.ai"],
    ["x", "https://x.com/Glyph_Os"],
    ["telegram", "https://t.me/Glyph_Os"],
  ];

  // We must size the TokenMetadata extension (variable length) and pass it into getMintLen(...)
  const tokenMetadataForSizing = {
    updateAuthority: treasury.publicKey,
    mint,
    name: NAME,
    symbol: SYMBOL,
    uri: METADATA_URI,
    additionalMetadata: ADDITIONAL,
  };

  const metadataPacked = pack(tokenMetadataForSizing);

  const extensions = [
    ExtensionType.TransferFeeConfig,
    ExtensionType.MetadataPointer,
    ExtensionType.TokenMetadata,
  ];

  const mintSpace = getMintLen(extensions, {
    [ExtensionType.TokenMetadata]: metadataPacked.length, // IMPORTANT
  });

  const lamportsForMint = await connection.getMinimumBalanceForRentExemption(mintSpace);

  const tx = new Transaction();

  // 1) Create mint account with enough space for extensions + variable metadata
  tx.add(
    SystemProgram.createAccount({
      fromPubkey: treasury.publicKey,
      newAccountPubkey: mint,
      space: mintSpace,
      lamports: lamportsForMint,
      programId: TOKEN_2022_PROGRAM_ID,
    })
  );

  // 2) Init transfer-fee config (tax)  [extensions generally init before mint]
  tx.add(
    createInitializeTransferFeeConfigInstruction(
      mint,
      feeConfigAuthority,
      withdrawWithheldAuthority,
      FEE_BPS,
      MAX_FEE_BASE,
      TOKEN_2022_PROGRAM_ID
    )
  );

  // 3) Init metadata pointer (store metadata IN the mint account itself)
  tx.add(
    createInitializeMetadataPointerInstruction(
      mint,
      treasury.publicKey, // authority to set pointer (we keep as treasury; harmless)
      mint,               // metadata address = mint
      TOKEN_2022_PROGRAM_ID
    )
  );

  // 4) Init mint
  tx.add(
    createInitializeMintInstruction(
      mint,
      DECIMALS,
      mintAuthority,
      freezeAuthority,
      TOKEN_2022_PROGRAM_ID
    )
  );

  // 5) Init token metadata (name/symbol/uri)
  tx.add(
    createInitializeTokenMetadataInstruction({
      programId: TOKEN_2022_PROGRAM_ID,
      metadata: mint, // stored in mint account
      updateAuthority: treasury.publicKey,
      mint,
      mintAuthority: treasury.publicKey,
      name: NAME,
      symbol: SYMBOL,
      uri: METADATA_URI,
    })
  );

  // 6) Add extra metadata fields
  for (const [field, value] of ADDITIONAL) {
    tx.add(
      createUpdateFieldInstruction({
        programId: TOKEN_2022_PROGRAM_ID,
        metadata: mint,
        updateAuthority: treasury.publicKey,
        field,
        value,
      })
    );
  }

  // Helper: ensure ATA + mint tokens
  const addMintTo = (owner: PublicKey, amountTokens: bigint) => {
    if (amountTokens === 0n) return;
    const ata = getAssociatedTokenAddressSync(mint, owner, false, TOKEN_2022_PROGRAM_ID);
    tx.add(
      createAssociatedTokenAccountIdempotentInstruction(
        treasury.publicKey,
        ata,
        owner,
        mint,
        TOKEN_2022_PROGRAM_ID
      )
    );
    tx.add(
      createMintToInstruction(
        mint,
        ata,
        mintAuthority,
        amountTokens * BASE,
        [],
        TOKEN_2022_PROGRAM_ID
      )
    );
  };

  // 7) Allocations (minted directly; minting is not “taxed”)
  if (DEV_WALLET && DEV_TOKENS > 0n) addMintTo(DEV_WALLET, DEV_TOKENS);
  if (MARKETING_WALLET && MARKETING_TOKENS > 0n) addMintTo(MARKETING_WALLET, MARKETING_TOKENS);

  // 8) Mint remainder to Treasury ATA
  const treasuryAta = getAssociatedTokenAddressSync(mint, treasury.publicKey, false, TOKEN_2022_PROGRAM_ID);
  tx.add(
    createAssociatedTokenAccountIdempotentInstruction(
      treasury.publicKey,
      treasuryAta,
      treasury.publicKey,
      mint,
      TOKEN_2022_PROGRAM_ID
    )
  );
  const remainderTokens = SUPPLY_TOKENS - allocTotal;
  tx.add(
    createMintToInstruction(
      mint,
      treasuryAta,
      mintAuthority,
      remainderTokens * BASE,
      [],
      TOKEN_2022_PROGRAM_ID
    )
  );

  // 9) OPTIONAL: lock metadata update authority to null
  if (LOCK_METADATA_AUTHORITY) {
    tx.add(
      createUpdateAuthorityInstruction({
        programId: TOKEN_2022_PROGRAM_ID,
        metadata: mint,
        oldAuthority: treasury.publicKey,
        newAuthority: null,
      })
    );
  }

  // 10) Revoke Mint authority (fixed supply)
  tx.add(
    createSetAuthorityInstruction(
      mint,
      mintAuthority,
      AuthorityType.MintTokens,
      null,
      [],
      TOKEN_2022_PROGRAM_ID
    )
  );

  // 11) Revoke Freeze authority (no freezing)
  tx.add(
    createSetAuthorityInstruction(
      mint,
      freezeAuthority,
      AuthorityType.FreezeAccount,
      null,
      [],
      TOKEN_2022_PROGRAM_ID
    )
  );

  // 12) Revoke TransferFeeConfig authority (fee params immutable)
  tx.add(
    createSetAuthorityInstruction(
      mint,
      feeConfigAuthority,
      AuthorityType.TransferFeeConfig,
      null,
      [],
      TOKEN_2022_PROGRAM_ID
    )
  );

  const sig = await sendAndConfirmTransaction(connection, tx, [treasury, mintKeypair], {
    commitment: "confirmed",
  });

  console.log("Token:", NAME, `(${SYMBOL})`);
  console.log("DECIMALS:", DECIMALS.toString());
  console.log("MINT:", mint.toBase58());
  console.log("TREASURY:", treasury.publicKey.toBase58());
  console.log("TREASURY_ATA:", treasuryAta.toBase58());
  console.log("TX:", sig);
  console.log("Fee bps:", FEE_BPS, "Max fee (base units):", MAX_FEE_BASE.toString());
  console.log("DEV minted:", DEV_WALLET ? DEV_TOKENS.toString() : "0");
  console.log("MARKETING minted:", MARKETING_WALLET ? MARKETING_TOKENS.toString() : "0");
  console.log("TREASURY remainder:", remainderTokens.toString());
  console.log("Metadata URI:", METADATA_URI);
  console.log("Metadata update locked:", LOCK_METADATA_AUTHORITY);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});