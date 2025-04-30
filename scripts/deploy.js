const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("📤 Deploying with address:", deployer.address);

  const buyer = "0x89F44431d03C175cd8758f69Aa1F9A5F89064Db4"; // ✅ Your buyer wallet
  const seller = "0xC8F9CbF2712fbA4e123D1855A4665544B6b535A9"; // ✅ Your seller wallet

  const Escrow = await hre.ethers.getContractFactory("Escrow");

  const escrow = await Escrow.deploy(buyer, seller, {
    value: hre.ethers.utils.parseEther("0.01"), // ✅ 0.01 MATIC for testing
  });

  await escrow.deployed();
  console.log("✅ Escrow Contract deployed to:", escrow.address);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

