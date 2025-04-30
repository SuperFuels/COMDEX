import { ethers } from "hardhat";

async function main() {
  const [deployer] = await ethers.getSigners();

  console.log("🚀 Deployer:", deployer.address);

  // Hardcoded buyer and seller addresses
  const buyer = "0x89F44431d03C175cd8758f69Aa1F9A5F89064Db4";
  const seller = "0xC8F9CbF2712fbA4e123D1855A4665544B6b535A9";

  const Escrow = await ethers.getContractFactory("Escrow");

  // Deploy Escrow contract with buyer, seller, and send 0.01 MATIC
  const escrow = await Escrow.deploy(buyer, seller, {
    value: ethers.parseEther("0.01"), // sending 0.01 MATIC to the escrow
  });

  await escrow.waitForDeployment();

  console.log("✅ Escrow contract deployed to:", await escrow.getAddress());
}

main().catch((error) => {
  console.error("❌ Deployment failed:", error);
  process.exit(1);
});

