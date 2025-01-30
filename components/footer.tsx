import Link from 'next/link'

export default function Footer() {
  return (
    <footer className="bg-white dark:bg-gray-900 text-gray-700 dark:text-gray-300 py-8 border-t border-gray-200 dark:border-gray-800">
      <div className="container mx-auto px-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div>
            <h3 className="text-lg font-semibold mb-4 text-blue-600 dark:text-blue-400">MQAI</h3>
            <p className="text-sm">Empowering AI-driven solutions</p>
            <p className="text-sm mt-2">MQAI.com Team - Developed by Daichi</p>
            {/* <p className="text-sm">Contact: team@mqai.com</p> */}
          </div>
          <div>
            <h4 className="text-lg font-semibold mb-4 text-blue-600 dark:text-blue-400">Quick Links</h4>
            <ul className="space-y-2">
              <li><Link href="/demo" className="text-sm hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Demo</Link></li>
              <li><Link href="/pricing" className="text-sm hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Pricing</Link></li>
              <li><Link href="/contact" className="text-sm hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Contact</Link></li>
            </ul>
          </div>
          <div>
            <h4 className="text-lg font-semibold mb-4 text-blue-600 dark:text-blue-400">Legal</h4>
            <ul className="space-y-2">
              <li><Link href="/privacy" className="text-sm hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Privacy Policy</Link></li>
              <li><Link href="/terms" className="text-sm hover:text-blue-600 dark:hover:text-blue-400 transition-colors">Terms of Service</Link></li>
            </ul>
          </div>
        </div>
        <div className="mt-8 pt-4 border-t border-gray-200 dark:border-gray-800 text-center text-sm">
          © {new Date().getFullYear()} MQAI. All rights reserved.
        </div>
      </div>
    </footer>
  )
}