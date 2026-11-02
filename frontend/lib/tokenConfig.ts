const token = {
  name: "Vortech Genetics",
  ticker: "VTGX",
  symbol: "$VTGX",
  quote: "USD",
} as const;

export const TOKEN_CONFIG = {
  ...token,
  pair: `${token.ticker}/${token.quote}`,
} as const;
