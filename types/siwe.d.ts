/**
 * Tell TS about the un-typed 'siwe' package
 */
declare module 'siwe' {
  export interface SiweMessageOpts {
    domain:   string
    address:  string
    statement:string
    uri:      string
    version:  string
    chainId:  number
    nonce:    string
  }
  export class SiweMessage {
    constructor(opts: SiweMessageOpts)
    prepareMessage(): string
  }
}
