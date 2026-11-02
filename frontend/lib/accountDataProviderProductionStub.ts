export function loadDemoProvider(): never {
  throw new Error("Development account providers are unavailable in production.");
}
