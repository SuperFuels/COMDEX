import { useEffect, useState } from "react";
import { ethers } from "ethers";
import { ESCROW_CONTRACT_ADDRESS, ESCROW_ABI } from "../constants/escrow";

export default function EscrowTest() {
  const [provider, setProvider] = useState<ethers.BrowserProvider>();
  const [signer, setSigner] = useState<ethers.Signer>();
  const [contract, setContract] = useState<ethers.Contract>();
  const [buyer, setBuyer] = useState("");
  const [seller, setSeller] = useState("");
  const [amount, setAmount] = useState("");
  const [isReleased, setIsReleased] = useState(false);
  const [isRefunded, setIsRefunded] = useState(false);
  const [balance, setBalance] = useState("");

  // 🔌 Wallet + Contract Connection
  useEffect(() => {
    async function init() {
      if (!window.ethereum) return alert("Please install MetaMask");

      const _provider = new ethers.BrowserProvider(window.ethereum);
      await _provider.send("eth_requestAccounts", []);
      const _signer = await _provider.getSigner();
      const _contract = new ethers.Contract(
        ESCROW_CONTRACT_ADDRESS,
        ESCROW_ABI,
        _signer
      );

      console.log("✅ Connected Wallet:", await _signer.getAddress());
      console.log("✅ Contract Loaded:", _contract.address);

      setProvider(_provider);
      setSigner(_signer);
      setContract(_contract);
    }

    init();
  }, []);

  // 📡 Fetch Data from Contract
  useEffect(() => {
    if (!contract) return;

    async function fetchData() {
      console.log("📡 Fetching on-chain contract data...");

      const _buyer = await contract.buyer();
      const _seller = await contract.seller();
      const _amount = await contract.amount();
      const _released = await contract.isReleased();
      const _refunded = await contract.isRefunded();
      const _balance = await contract.getBalance();

      console.log({
        _buyer,
        _seller,
        _amount: ethers.formatEther(_amount),
        _released,
        _refunded,
        _balance: ethers.formatEther(_balance),
      });

      setBuyer(_buyer);
      setSeller(_seller);
      setAmount(ethers.formatEther(_amount));
      setIsReleased(_released);
      setIsRefunded(_refunded);
      setBalance(ethers.formatEther(_balance));
    }

    fetchData();
  }, [contract]);

  // 🔘 Release funds to seller
  async function handleRelease() {
    if (!contract) return;
    const tx = await contract.releaseToSeller();
    await tx.wait();
    alert("✅ Released to Seller!");
  }

  // 🔘 Refund funds to buyer
  async function handleRefund() {
    if (!contract) return;
    const tx = await contract.refundToBuyer();
    await tx.wait();
    alert("✅ Refunded to Buyer!");
  }

  return (
    <div style={{ padding: "2rem" }}>
      <h1>🤝 Escrow Contract Interaction</h1>
      <p>This page is ready to interact with your deployed smart contract.</p>

      <div style={{ marginTop: "2rem" }}>
        <p><strong>Buyer:</strong> {buyer}</p>
        <p><strong>Seller:</strong> {seller}</p>
        <p><strong>Amount:</strong> {amount} ETH</p>
        <p><strong>Contract Balance:</strong> {balance} ETH</p>
        <p><strong>Released:</strong> {isReleased ? "✅ Yes" : "❌ No"}</p>
        <p><strong>Refunded:</strong> {isRefunded ? "✅ Yes" : "❌ No"}</p>
      </div>

      <div style={{ marginTop: "2rem" }}>
        <button onClick={handleRelease} style={{ marginRight: "1rem" }}>
          🔓 Release to Seller
        </button>
        <button onClick={handleRefund}>
          🔙 Refund to Buyer
        </button>
      </div>
    </div>
  );
}

