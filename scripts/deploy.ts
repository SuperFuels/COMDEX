import hre from "hardhat";

async function main() {
  // Grab the deployer signer
  const [deployer] = await hre.ethers.getSigners();
  console.log("🚀 Deploying with:", deployer.address);

  // Hard-coded buyer / seller for now
  const buyer  = "0x89F44431d03C175cd8758f69Aa1F9A5F89064Db4";
  const seller = "0xC8F9CbF2712fbA4e123D1855A4665544B6b535A9";

  // Compile & grab factory
  const Escrow = await hre.ethers.getContractFactory("Escrow");

  // Deploy with 0.01 MATIC upfront
  const escrow = await Escrow.deploy(buyer, seller, {
    // ethers v5 style: use utils.parseEther
    value: hre.ethers.utils.parseEther("0.01"),
  });

  await escrow.deployed();
  console.log("✅ Escrow deployed to:", escrow.address);
}

main().catch((err) => {
  console.error("❌ Deployment failed:", err);
  process.exit(1);
});
