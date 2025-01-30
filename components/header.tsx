"use client"

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Menu, X, User, LogOut } from 'lucide-react'
import { useAuth } from '@/context/auth-context'
import { Skeleton } from '@/components/ui/skeleton'
// import Logo from '@/public/logo.png' 

export default function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [mounted, setMounted] = useState(false)
  const { isAuthenticated, isLoading, user, logout } = useAuth()

  useEffect(() => {
    setMounted(true)
  }, [])

  // Show a consistent loading state during both server and client render
  if (!mounted || isLoading) {
    return (
      <header className="fixed top-0 left-0 right-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md shadow-md">
        <div className="container mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div className="text-4xl font-extrabold gradient-text">MQAI</div>
            <nav className="hidden md:flex space-x-4">
              <Skeleton className="h-10 w-20" />
              <Skeleton className="h-10 w-20" />
            </nav>
          </div>
        </div>
      </header>
    )
  }

  const menuItems = isAuthenticated ? [
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/profile', label: 'Profile' },
  ] : [
    { href: '/demo', label: 'Demo' },
    { href: '/pricing', label: 'Pricing' },
    { href: '/contact', label: 'Contact' },
  ]

  return (
    <motion.header
      initial={{ y: -100 }}
      animate={{ y: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="fixed top-0 left-0 right-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md shadow-md"
    >
      <div className="container mx-auto px-4 py-4">
        <div className="flex justify-between items-center">
          <Link href="/">
            <div className="text-4xl font-extrabold gradient-text">MQAI</div>
          </Link>
          <nav className="hidden md:flex space-x-4">
            {menuItems.map((item) => (
              <Link key={item.href} href={item.href}>
                <Button variant="ghost" className="text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400">
                  {item.label}
                </Button>
              </Link>
            ))}
            {isAuthenticated && user ? (
              <div className="flex items-center space-x-4">
                <Button variant="ghost" className="text-gray-700 dark:text-gray-300">
                  <User className="w-4 h-4 mr-2" />
                  {user.name}
                </Button>
                <Button 
                  variant="outline" 
                  onClick={logout}
                  className="text-red-600 dark:text-red-400 border-red-600 dark:border-red-400 hover:bg-red-600 hover:text-white"
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Logout
                </Button>
              </div>
            ) : (
              <>
                <Link href="/login">
                  <Button variant="outline" className="text-blue-600 dark:text-blue-400 border-blue-600 dark:border-blue-400 hover:bg-blue-600 hover:text-white dark:hover:bg-blue-400 dark:hover:text-gray-900">
                    Login
                  </Button>
                </Link>
                <Link href="/signup">
                  <Button variant="default" className="bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:text-gray-900 dark:hover:bg-blue-400">
                    Sign Up
                  </Button>
                </Link>
              </>
            )}
          </nav>
          <button className="md:hidden text-gray-700 dark:text-gray-300" onClick={() => setIsMenuOpen(!isMenuOpen)}>
            {isMenuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </div>
      {isMenuOpen && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          className="md:hidden bg-white dark:bg-gray-900"
        >
          <nav className="flex flex-col items-center space-y-4 py-4">
            {menuItems.map((item) => (
              <Link key={item.href} href={item.href}>
                <Button variant="ghost" className="w-full text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400">
                  {item.label}
                </Button>
              </Link>
            ))}
            {isAuthenticated ? (
              <>
                <Button variant="ghost" className="w-full text-gray-700 dark:text-gray-300">
                  <User className="w-4 h-4 mr-2" />
                  {user?.name}
                </Button>
                <Button 
                  variant="outline" 
                  onClick={logout}
                  className="w-full text-red-600 dark:text-red-400 border-red-600 dark:border-red-400 hover:bg-red-600 hover:text-white"
                >
                  <LogOut className="w-4 h-4 mr-2" />
                  Logout
                </Button>
              </>
            ) : (
              <>
                <Link href="/login" className="w-full px-4">
                  <Button variant="outline" className="w-full text-blue-600 dark:text-blue-400 border-blue-600 dark:border-blue-400 hover:bg-blue-600 hover:text-white">
                    Login
                  </Button>
                </Link>
                <Link href="/signup" className="w-full px-4">
                  <Button variant="default" className="w-full bg-blue-600 text-white hover:bg-blue-700">
                    Sign Up
                  </Button>
                </Link>
              </>
            )}
          </nav>
        </motion.div>
      )}
    </motion.header>
  )
}