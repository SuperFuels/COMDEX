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
} from "@solana/spl-token";

// ---- CONFIG ----
const RPC = process.env.RPC ?? "https://api.mainnet-beta.solana.com";
const TREASURY_KEYPAIR = process.env.TREASURY_KEYPAIR ?? "";

if (!TREASURY_KEYPAIR) {
  throw new Error("Set TREASURY_KEYPAIR to the path of your treasury keypair json");
}

// Token params (Glyph Internet Protocol)
const NAME = "Glyph Internet Protocol";
const SYMBOL = "GIP";
const DECIMALS = 8;                    
const SUPPLY_TOKENS = 100_000_000_000n; // 100Bn

// Transfer fee params
const FEE_BPS = 300; // 3%
const MAX_FEE_TOKENS = 100_000_000n; // cap per transfer

// Optional allocations (minted directly, NOT taxed)
const DEV_WALLET = process.env.DEV_WALLET ? new PublicKey(process.env.DEV_WALLET) : null;
const DEV_TOKENS = process.env.DEV_TOKENS ? BigInt(process.env.DEV_TOKENS) : 0n;

const MARKETING_WALLET = process.env.MARKETING_WALLET ? new PublicKey(process.env.MARKETING_WALLET) : null;
const MARKETING_TOKENS = process.env.MARKETING_TOKENS ? BigInt(process.env.MARKETING_TOKENS) : 0n;

const BASE = 10n ** BigInt(DECIMALS);
const MAX_FEE_BASE = MAX_FEE_TOKENS * BASE; // 1e17

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

  const allocTotal = (DEV_WALLET ? DEV_TOKENS : 0n) + (MARKETING_WALLET ? MARKETING_TOKENS : 0n);
  if (allocTotal > SUPPLY_TOKENS) {
    throw new Error("DEV_TOKENS + MARKETING_TOKENS exceeds total supply");
  }

  // Authorities (all start as treasury, then revoke what we don’t want)
  const mintAuthority = treasury.publicKey;
  const feeConfigAuthority = treasury.publicKey;         // revoke after setup
  const withdrawWithheldAuthority = treasury.publicKey;  // keep (this collects tax)
  const freezeAuthority = treasury.publicKey;            // revoke

  // Create mint account sized for TransferFeeConfig
  const extensions = [ExtensionType.TransferFeeConfig];
  const mintLen = getMintLen(extensions);
  const lamportsForMint = await connection.getMinimumBalanceForRentExemption(mintLen);

  const mintKeypair = Keypair.generate();
  const mint = mintKeypair.publicKey;

  // Helper: ensure ATA + mint tokens
  const addMintTo = (tx: Transaction, owner: PublicKey, amountTokens: bigint) => {
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

  const tx = new Transaction();

  // 1) Create mint account
  tx.add(
    SystemProgram.createAccount({
      fromPubkey: treasury.publicKey,
      newAccountPubkey: mint,
      space: mintLen,
      lamports: lamportsForMint,
      programId: TOKEN_2022_PROGRAM_ID,
    })
  );

  // 2) Init transfer-fee config
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

  // 3) Init mint
  tx.add(
    createInitializeMintInstruction(
      mint,
      DECIMALS,
      mintAuthority,
      freezeAuthority,
      TOKEN_2022_PROGRAM_ID
    )
  );

  // 4) Optional allocations (minted directly, no transfer fee)
  if (DEV_WALLET && DEV_TOKENS > 0n) addMintTo(tx, DEV_WALLET, DEV_TOKENS);
  if (MARKETING_WALLET && MARKETING_TOKENS > 0n) addMintTo(tx, MARKETING_WALLET, MARKETING_TOKENS);

  // 5) Mint remainder to Treasury ATA
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

  // 6) Revoke Mint authority (fixed supply forever)
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

  // 7) Revoke Freeze authority (no freezing)
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

  // 8) Revoke TransferFeeConfig authority (fee settings become immutable)
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
  console.log("MINT:", mint.toBase58());
  console.log("TREASURY:", treasury.publicKey.toBase58());
  console.log("TREASURY_ATA:", treasuryAta.toBase58());
  console.log("TX:", sig);
  console.log("Fee bps:", FEE_BPS, "Max fee (base units):", MAX_FEE_BASE.toString());
  console.log("Minted DEV tokens:", DEV_WALLET ? DEV_TOKENS.toString() : "0");
  console.log("Minted MARKETING tokens:", MARKETING_WALLET ? MARKETING_TOKENS.toString() : "0");
  console.log("Minted TREASURY remainder:", remainderTokens.toString()); // 85,000,000,000 tokens
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});