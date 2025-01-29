import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { ThemeProvider } from '@/components/theme-provider'
import { AuthProvider } from '@/context/auth-context'
import { Toaster } from 'sonner'
import Header from '@/components/header'
import Footer from '@/components/footer'
import FloatingThemeToggle from '@/components/floating-theme-toggle'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'SubtitleAI - Advanced Video Subtitle Generator',
  description: 'Generate and translate subtitles for your videos using AI',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.className} min-h-screen flex flex-col bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800`} suppressHydrationWarning>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <AuthProvider>
            <div suppressHydrationWarning>
              <Header />
              <main className="flex-grow container mx-auto px-4 py-8 mt-16">
                {children}
              </main>
              <Footer />
              <FloatingThemeToggle />
              <Toaster />
            </div>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}