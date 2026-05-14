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

// TLV header sizing for Token-2022 metadata extension payload
const TYPE_SIZE = 2; // u16
const LENGTH_SIZE = 2; // u16

// ---- CONFIG (env) ----
const RPC = process.env.RPC ?? "https://api.mainnet-beta.solana.com";
const TREASURY_KEYPAIR = process.env.TREASURY_KEYPAIR ?? "";
if (!TREASURY_KEYPAIR) throw new Error("Set TREASURY_KEYPAIR to path of your treasury keypair json");

const DEV_WALLET = process.env.DEV_WALLET ? new PublicKey(process.env.DEV_WALLET) : null;
const DEV_TOKENS = process.env.DEV_TOKENS ? BigInt(process.env.DEV_TOKENS) : 0n;

const MARKETING_WALLET = process.env.MARKETING_WALLET ? new PublicKey(process.env.MARKETING_WALLET) : null;
const MARKETING_TOKENS = process.env.MARKETING_TOKENS ? BigInt(process.env.MARKETING_TOKENS) : 0n;

// Hosted JSON URI (must be live/200)
const METADATA_URI = process.env.URI ?? "";
if (!METADATA_URI) throw new Error("Set URI to your hosted metadata JSON (must be 200 OK)");

// Token params
const NAME = "Glyph Internet Protocol";
const SYMBOL = "GIP";
const DECIMALS = 8;                     // 100Bn + 9 decimals can overflow u64 on mint amounts
const SUPPLY_TOKENS = 100_000_000_000n; // 100Bn

// Transfer fee params
const FEE_BPS = 300;                 // 3%
const MAX_FEE_TOKENS = 100_000_000n; // cap per transfer

// If true, locks metadata update authority to null (URI can still point to JSON you can change)
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

  const allocTotal = (DEV_WALLET ? DEV_TOKENS : 0n) + (MARKETING_WALLET ? MARKETING_TOKENS : 0n);
  if (allocTotal > SUPPLY_TOKENS) throw new Error("DEV_TOKENS + MARKETING_TOKENS exceeds total supply");

  // Authorities start as treasury, then revoke what we don’t want
  const mintAuthority = treasury.publicKey;
  const feeConfigAuthority = treasury.publicKey;        // revoke after setup
  const withdrawWithheldAuthority = treasury.publicKey; // KEEP (collects transfer tax)
  const freezeAuthority = treasury.publicKey;           // revoke after setup

  // --- Extensions we want on the mint
  // TransferFeeConfig (tax), MetadataPointer (points to where Token-2022 metadata lives)
  const extensions = [ExtensionType.TransferFeeConfig, ExtensionType.MetadataPointer];

  const mintLenBase = getMintLen(extensions);

  // New mint
  const mintKeypair = Keypair.generate();
  const mint = mintKeypair.publicKey;

  // Token-2022 metadata "additionalMetadata" MUST be tuple pairs
  const ADDITIONAL: Array<[string, string]> = [
    ["website", "https://www.tessaris.ai"],
    ["x", "https://x.com/Glyph_Os"],
    ["telegram", "https://t.me/Glyph_Os"],
  ];

  // Used ONLY for sizing pack(); must include the real mint pubkey
  const tokenMetadataForSizing = {
    updateAuthority: treasury.publicKey,
    mint,
    name: NAME,
    symbol: SYMBOL,
    uri: METADATA_URI,
    additionalMetadata: ADDITIONAL,
  };

  const metadataPacked = pack(tokenMetadataForSizing);
  const metadataSpace = TYPE_SIZE + LENGTH_SIZE + metadataPacked.length;

  // Total mint space = base mint + our metadata payload space
  const mintSpace = mintLenBase + metadataSpace;
  const lamportsForMint = await connection.getMinimumBalanceForRentExemption(mintSpace);

  const tx = new Transaction();

  // 1) Create mint account
  tx.add(
    SystemProgram.createAccount({
      fromPubkey: treasury.publicKey,
      newAccountPubkey: mint,
      space: mintSpace,
      lamports: lamportsForMint,
      programId: TOKEN_2022_PROGRAM_ID,
    })
  );

  // 2) Init transfer fee config
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

  // 4) Init metadata pointer (store metadata inside the mint account itself)
  tx.add(
    createInitializeMetadataPointerInstruction(
      mint,
      treasury.publicKey, // pointer authority (we can revoke later if you want)
      mint,               // metadata address = mint (in-mint metadata)
      TOKEN_2022_PROGRAM_ID
    )
  );

  // 5) Init token metadata (name/symbol/uri)
  tx.add(
    createInitializeTokenMetadataInstruction({
      programId: TOKEN_2022_PROGRAM_ID,
      metadata: mint, // stored in the mint account
      updateAuthority: treasury.publicKey,
      mint,
      mintAuthority: treasury.publicKey,
      name: NAME,
      symbol: SYMBOL,
      uri: METADATA_URI,
    })
  );

  // 6) Add extra fields (nice-to-have)
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

  // 7) Allocations (minted directly; not “taxed”)
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

  // 9) Revoke mint authority (fixed supply forever)
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

  // 10) Revoke freeze authority (no freezing)
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

  // 11) Revoke TransferFeeConfig authority (fee settings become immutable)
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

  // 12) Optional: lock Token-2022 metadata update authority
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

  // (Optional but recommended) revoke MetadataPointer authority so pointer can’t be changed later
  tx.add(
    createSetAuthorityInstruction(
      mint,
      treasury.publicKey,
      AuthorityType.MetadataPointer,
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