// hardhat.config.ts
import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";

dotenv.config();

// make sure these are defined in your .env / Cloud Run:
// WEB3_PROVIDER_URL – your RPC endpoint (Alchemy, Infura, etc.)
// DEPLOYER_PRIVATE_KEY – the single key string to deploy with
// MNEMONIC – optional 12-word mnemonic, for localhost / forked chains

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: { enabled: true, runs: 200 },
    },
  },

  defaultNetwork: "localhost",

  networks: {
    // ▶︎ Local Hardhat node
    localhost: {
      url: process.env.WEB3_PROVIDER_URL ?? "http://127.0.0.1:8545",
      accounts: process.env.MNEMONIC
        ? { mnemonic: process.env.MNEMONIC }
        : undefined,
    },

    // ▶︎ Polygon Mumbai testnet
    mumbai: {
      url: process.env.WEB3_PROVIDER_URL,
      chainId: 80001,
      accounts: process.env.DEPLOYER_PRIVATE_KEY
        ? [process.env.DEPLOYER_PRIVATE_KEY]
        : [],
    },

    // ▶︎ Mainnet (if you ever need it)
    polygon: {
      url: process.env.WEB3_PROVIDER_URL,
      chainId: 137,
      accounts: process.env.DEPLOYER_PRIVATE_KEY
        ? [process.env.DEPLOYER_PRIVATE_KEY]
        : [],
    },
  },

  etherscan: {
    // If you want to verify on polygonscan add:
    apiKey: process.env.POLYGONSCAN_API_KEY || "",
  },
};

export default config;
