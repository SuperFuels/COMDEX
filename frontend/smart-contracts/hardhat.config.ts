import hardhatEthers from "@nomicfoundation/hardhat-ethers";
import { configVariable, defineConfig } from "hardhat/config";

export default defineConfig({
  plugins: [hardhatEthers],
  solidity: {
    version: "0.8.20",
  },
  networks: {
    hardhatMainnet: {
      type: "edr-simulated",
      chainType: "l1",
    },
    localhost: {
      type: "http",
      chainType: "l1",
      url: "http://127.0.0.1:8545",
      chainId: 31337,
    },
    polygon: {
      type: "http",
      chainType: "generic",
      url: configVariable("POLYGON_RPC_URL"),
      accounts: [configVariable("PRIVATE_KEY")],
      chainId: 137,
    },
  },
});
