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
  TOKEN_2022_PROGRAM_ID,
  ExtensionType,
  getMintLen,
  getAssociatedTokenAddressSync,
  createInitializeMintInstruction,
  createInitializeTransferFeeConfigInstruction,
  createAssociatedTokenAccountIdempotentInstruction,
  createMintToInstruction,
  createSetAuthorityInstruction,
  AuthorityType,
  createInitializeMetadataPointerInstruction,
} from "@solana/spl-token";

import {
  createInitializeInstruction as createInitializeTokenMetadataInstruction,
  createUpdateFieldInstruction,
  createUpdateAuthorityInstruction,
  pack,
  type TokenMetadata,
} from "@solana/spl-token-metadata";

const TYPE_SIZE = 2;   // u16
const LENGTH_SIZE = 2; // u16

// ---- CONFIG (env) ----
const RPC = process.env.RPC ?? "https://api.mainnet-beta.solana.com";
const TREASURY_KEYPAIR = process.env.TREASURY_KEYPAIR ?? "";
if (!TREASURY_KEYPAIR) throw new Error("Set TREASURY_KEYPAIR to path of your treasury keypair json");

const DEV_WALLET = process.env.DEV_WALLET ? new PublicKey(process.env.DEV_WALLET) : null;
const DEV_TOKENS = process.env.DEV_TOKENS ? BigInt(process.env.DEV_TOKENS) : 0n;

const MARKETING_WALLET = process.env.MARKETING_WALLET ? new PublicKey(process.env.MARKETING_WALLET) : null;
const MARKETING_TOKENS = process.env.MARKETING_TOKENS ? BigInt(process.env.MARKETING_TOKENS) : 0n;

// Hosted JSON URI (must be live)
const METADATA_URI = process.env.URI ?? "";
if (!METADATA_URI) throw new Error("Set URI to your hosted metadata JSON (must be 200 OK)");

// Token params
const NAME = "Glyph Internet Protocol";
const SYMBOL = "GIP";
const DECIMALS = 8;
const SUPPLY_TOKENS = 100_000_000_000n;

// Transfer fee params
const FEE_BPS = 300;                 // 3%
const MAX_FEE_TOKENS = 100_000_000n; // cap per transfer

// If true, lock metadata update authority to null (URI remains, you can update JSON behind it)
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

async function sendTxOrDie(
  connection: Connection,
  tx: Transaction,
  signers: Keypair[],
  label: string
) {
  try {
    const sig = await sendAndConfirmTransaction(connection, tx, signers, { commitment: "confirmed" });
    console.log(`${label}:`, sig);
    return sig;
  } catch (e: any) {
    console.error(`${label} failed:`, e?.message || e);
    if (e instanceof SendTransactionError) {
      const logs = await e.getLogs(connection);
      console.log(`${label} full logs:\n` + (logs || []).join("\n"));
    } else if (e?.transactionLogs) {
      console.log(`${label} transactionLogs:\n` + e.transactionLogs.join("\n"));
    }
    process.exit(1);
  }
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
  const withdrawWithheldAuthority = treasury.publicKey;  // KEEP (this collects the transfer tax)
  const freezeAuthority = treasury.publicKey;            // will revoke

  // Create mint with extensions:
  // - TransferFeeConfig (tax)
  // - MetadataPointer (points to where Token-2022 metadata lives; we point to the mint itself)
  const extensions = [ExtensionType.TransferFeeConfig, ExtensionType.MetadataPointer];

  // Generate mint pubkey first (needed for sizing + metadata)
  const mintKeypair = Keypair.generate();
  const mint = mintKeypair.publicKey;

  const ADDITIONAL: Array<[string, string]> = [
    ["website", "https://www.tessaris.ai"],
    ["x", "https://x.com/Glyph_Os"],
    ["telegram", "https://t.me/Glyph_Os"],
  ];

  // Size mint for metadata stored in the mint account (Token-2022 metadata TLV appended)
  const tokenMetadataForSizing: TokenMetadata = {
    updateAuthority: treasury.publicKey,
    mint,
    name: NAME,
    symbol: SYMBOL,
    uri: METADATA_URI,
    additionalMetadata: ADDITIONAL,
  };

  const mintLenBase = getMintLen(extensions);
  const metadataPacked = pack(tokenMetadataForSizing);
  const metadataSpace = TYPE_SIZE + LENGTH_SIZE + metadataPacked.length;
  const mintSpace = mintLenBase + metadataSpace;

  const lamportsForMint = await connection.getMinimumBalanceForRentExemption(mintSpace);

  const treasuryBal = await connection.getBalance(treasury.publicKey, "confirmed");
  console.log("Treasury:", treasury.publicKey.toBase58());
  console.log("Treasury balance:", (treasuryBal / 1e9).toFixed(6), "SOL");
  console.log("Mint space bytes:", mintSpace, "rent SOL:", (lamportsForMint / 1e9).toFixed(6));

  // ---- TX1: create mint + InitializeMint + TransferFeeConfig ----
  {
    const tx1 = new Transaction();

    tx1.add(
      SystemProgram.createAccount({
        fromPubkey: treasury.publicKey,
        newAccountPubkey: mint,
        space: mintSpace,
        lamports: lamportsForMint,
        programId: TOKEN_2022_PROGRAM_ID,
      })
    );

    // ✅ Initialize the mint FIRST
    tx1.add(
      createInitializeMintInstruction(
        mint,
        DECIMALS,
        mintAuthority,
        freezeAuthority,
        TOKEN_2022_PROGRAM_ID
      )
    );

    // ✅ Then set transfer fee config
    tx1.add(
      createInitializeTransferFeeConfigInstruction(
        mint,
        feeConfigAuthority,
        withdrawWithheldAuthority,
        FEE_BPS,
        MAX_FEE_BASE,
        TOKEN_2022_PROGRAM_ID
      )
    );

    await sendTxOrDie(connection, tx1, [treasury, mintKeypair], "TX1 (create+init mint+fee)");
  }

  // ---- TX2: initialize metadata pointer + initialize token-2022 metadata + extra fields + (optional) lock ----
  {
    const tx2 = new Transaction();

    tx2.add(
      createInitializeMetadataPointerInstruction(
        mint,
        treasury.publicKey, // pointer authority
        mint,               // metadata address = mint (store metadata in mint account)
        TOKEN_2022_PROGRAM_ID
      )
    );

    tx2.add(
      createInitializeTokenMetadataInstruction({
        programId: TOKEN_2022_PROGRAM_ID,
        metadata: mint, // metadata stored in mint account
        updateAuthority: treasury.publicKey,
        mint,
        mintAuthority: treasury.publicKey,
        name: NAME,
        symbol: SYMBOL,
        uri: METADATA_URI,
      })
    );

    for (const [k, v] of ADDITIONAL) {
      tx2.add(
        createUpdateFieldInstruction({
          programId: TOKEN_2022_PROGRAM_ID,
          metadata: mint,
          updateAuthority: treasury.publicKey,
          field: k,
          value: v,
        })
      );
    }

    if (LOCK_METADATA_AUTHORITY) {
      tx2.add(
        createUpdateAuthorityInstruction({
          programId: TOKEN_2022_PROGRAM_ID,
          metadata: mint,
          oldAuthority: treasury.publicKey,
          newAuthority: null,
        })
      );
    }

    await sendTxOrDie(connection, tx2, [treasury], "TX2 (pointer+token2022-metadata)");
  }

  // ---- TX3: create ATAs + mint supply + revoke authorities ----
  {
    const tx3 = new Transaction();

    const addMintTo = (owner: PublicKey, amountTokens: bigint) => {
      if (amountTokens === 0n) return;

      const ata = getAssociatedTokenAddressSync(mint, owner, false, TOKEN_2022_PROGRAM_ID);

      tx3.add(
        createAssociatedTokenAccountIdempotentInstruction(
          treasury.publicKey,
          ata,
          owner,
          mint,
          TOKEN_2022_PROGRAM_ID
        )
      );

      tx3.add(
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

    if (DEV_WALLET && DEV_TOKENS > 0n) addMintTo(DEV_WALLET, DEV_TOKENS);
    if (MARKETING_WALLET && MARKETING_TOKENS > 0n) addMintTo(MARKETING_WALLET, MARKETING_TOKENS);

    const treasuryAta = getAssociatedTokenAddressSync(mint, treasury.publicKey, false, TOKEN_2022_PROGRAM_ID);
    tx3.add(
      createAssociatedTokenAccountIdempotentInstruction(
        treasury.publicKey,
        treasuryAta,
        treasury.publicKey,
        mint,
        TOKEN_2022_PROGRAM_ID
      )
    );

    const remainderTokens = SUPPLY_TOKENS - allocTotal;
    tx3.add(
      createMintToInstruction(
        mint,
        treasuryAta,
        mintAuthority,
        remainderTokens * BASE,
        [],
        TOKEN_2022_PROGRAM_ID
      )
    );

    // Revoke Mint authority (fixed supply)
    tx3.add(
      createSetAuthorityInstruction(
        mint,
        mintAuthority,
        AuthorityType.MintTokens,
        null,
        [],
        TOKEN_2022_PROGRAM_ID
      )
    );

    // Revoke Freeze authority
    tx3.add(
      createSetAuthorityInstruction(
        mint,
        freezeAuthority,
        AuthorityType.FreezeAccount,
        null,
        [],
        TOKEN_2022_PROGRAM_ID
      )
    );

    // Revoke TransferFeeConfig authority (fee params immutable)
    tx3.add(
      createSetAuthorityInstruction(
        mint,
        feeConfigAuthority,
        AuthorityType.TransferFeeConfig,
        null,
        [],
        TOKEN_2022_PROGRAM_ID
      )
    );

    await sendTxOrDie(connection, tx3, [treasury], "TX3 (mint+revoke)");
  }

  console.log("----- DONE -----");
  console.log("MINT:", mint.toBase58());
  console.log("TREASURY:", treasury.publicKey.toBase58());
  console.log("URI:", METADATA_URI);
  console.log("Metadata update locked:", LOCK_METADATA_AUTHORITY);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});