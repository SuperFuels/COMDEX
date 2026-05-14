async function main() {
  const [deployer] = await ethers.getSigners();
  console.log("Deploying with:", deployer.address);

  const GLU = await ethers.getContractFactory("GLU");
  const glu = await GLU.deploy(ethers.utils.parseUnits("10000000", 18));
  await glu.deployed();
  console.log("GLU deployed to:", glu.address);

  const Escrow = await ethers.getContractFactory("GLUEscrow");
  const escrow = await Escrow.deploy(glu.address);
  await escrow.deployed();
  console.log("Escrow deployed to:", escrow.address);
}

main()
  .then(() => process.exit(0))
  .catch(e => {
    console.error(e);
    process.exit(1);
  });
