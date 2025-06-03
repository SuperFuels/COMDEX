// frontend/constants/escrow.ts

export const ESCROW_CONTRACT_ADDRESS = "0x9a791Cd653EBb3F87CF424Fb490E14cdB0ACbD28";

export const ESCROW_ABI = [
  {
    "inputs": [
      { "internalType": "address", "name": "_buyer",  "type": "address" },
      { "internalType": "address", "name": "_seller", "type": "address" }
    ],
    "stateMutability": "payable",
    "type": "constructor"
  },
  // … rest of your ABI …
  { 
    "inputs": [], 
    "name": "seller", 
    "outputs": [
      { "internalType": "address", "name": "", "type": "address" }
    ],
    "stateMutability": "view",
    "type": "function"
  }
];