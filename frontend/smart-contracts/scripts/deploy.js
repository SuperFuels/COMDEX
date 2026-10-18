import { network } from "hardhat";

async function main() {
  const { ethers } = await network.create();
  const [deployer] = await ethers.getSigners();
  console.log("Deploying with:", deployer.address);

  const GLU = await ethers.getContractFactory("GLU");
  const glu = await GLU.deploy(ethers.parseUnits("10000000", 18));
  await glu.waitForDeployment();
  const gluAddress = await glu.getAddress();
  console.log("GLU deployed to:", gluAddress);

  const Escrow = await ethers.getContractFactory("GLUEscrow");
  const escrow = await Escrow.deploy(gluAddress);
  await escrow.waitForDeployment();
  console.log("Escrow deployed to:", await escrow.getAddress());
}

main()
  .then(() => process.exit(0))
  .catch(e => {
    console.error(e);
    process.exit(1);
  });
