// hardhat.config.ts

import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";

dotenv.config();

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.20",
    settings: {
      optimizer: {
        enabled: true,
        runs: 200,
      },
    },
  },

  // Make localhost the default network for `npx hardhat node` and scripts
  defaultNetwork: "localhost",

  networks: {
    // Local Hardhat network
    localhost: {
      url: process.env.WEB3_PROVIDER_URL || "http://127.0.0.1:8545",
      accounts: {
        mnemonic:
          process.env.MNEMONIC ||
          "test test test test test test test test test test test junk",
      },
    },

    // Amoy / testnet configuration (optional)
    amoy: {
      url:
        process.env.ALCHEMY_URL ||
        "https://polygon-amoy.g.network",
      accounts: process.env.PRIVATE_KEY
        ? [process.env.PRIVATE_KEY]
        : [
            // fallback to Hardhat's first default account key
            "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
          ],
    },
  },
};

export default config;

