// hardhat.config.ts
import { HardhatUserConfig } from "hardhat/config";
import "@nomicfoundation/hardhat-toolbox";
import * as dotenv from "dotenv";
dotenv.config();

const LOCAL_RPC = "http://127.0.0.1:8545";
const RPC = process.env.WEB3_PROVIDER_URL ?? LOCAL_RPC;

const config: HardhatUserConfig = {
  solidity: {
    version: "0.8.20",
    settings: { optimizer: { enabled: true, runs: 200 } },
  },

  defaultNetwork: "localhost",

  networks: {
    localhost: {
      url: LOCAL_RPC,
      // if you want to use a mnemonic locally:
      accounts: process.env.MNEMONIC ? { mnemonic: process.env.MNEMONIC } : undefined,
    },
    mumbai: {
      url: RPC,
      chainId: 80001,
      accounts: process.env.DEPLOYER_PRIVATE_KEY
        ? [process.env.DEPLOYER_PRIVATE_KEY]
        : [],
    },
    polygon: {
      url: RPC,
      chainId: 137,
      accounts: process.env.DEPLOYER_PRIVATE_KEY
        ? [process.env.DEPLOYER_PRIVATE_KEY]
        : [],
    },
  },

  etherscan: {
    apiKey: process.env.POLYGONSCAN_API_KEY || "",
  },
};

export default config;