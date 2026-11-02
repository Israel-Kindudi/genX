import NextAuth from "next-auth"
import GoogleProvider from "next-auth/providers/google"

const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID as string,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET as string,
    }),
  ],
  callbacks: {
    async signIn({ user, account, profile }) {
      if (account?.provider === "google") {
        try {
          // Send user to our FastAPI backend to generate a JWT
          const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/api/auth/google-login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: user.email,
              full_name: user.name,
              google_id: profile?.sub
            })
          });
          
          if (res.ok) {
            const data = await res.json();
            // Store the FastAPI JWT
            localStorage.setItem("genx_token", data.access_token);
            return true;
          }
          return false;
        } catch (error) {
          console.error("Google auth backend error", error);
          return false;
        }
      }
      return true;
    },
  },
  pages: {
    signIn: '/login', // Fallback to our custom login page
  },
})

export { handler as GET, handler as POST }