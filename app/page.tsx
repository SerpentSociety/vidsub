"use client"

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Progress } from '@/components/ui/progress'
import { Card, CardContent } from '@/components/ui/card'
import { Upload, Check, RefreshCw, ArrowRight, AlertCircle } from 'lucide-react'
import { VideoService } from '@/lib/services/video'
import { useToast } from '@/hooks/use-toast'
import { Alert, AlertDescription } from '@/components/ui/alert'

const MAX_FILE_SIZE = 500 * 1024 * 1024 // 500MB
const ALLOWED_TYPES = ['video/mp4', 'video/quicktime', 'video/x-msvideo', 'video/webm']

export default function Home() {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const router = useRouter()
  const { toast } = useToast()

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null)
    if (e.target.files) {
      const selectedFile = e.target.files[0]
      
      if (!ALLOWED_TYPES.includes(selectedFile.type)) {
        setError('Please select a valid video file (MP4, MOV, AVI, or WebM)')
        return
      }

      if (selectedFile.size > MAX_FILE_SIZE) {
        setError('Please select a video file under 500MB')
        return
      }

      setFile(selectedFile)
      setVideoUrl(URL.createObjectURL(selectedFile))
    }
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setError(null)
    
    try {
      const response = await VideoService.uploadVideo(file)
      
      localStorage.setItem('uploadedVideo', JSON.stringify({
        id: response.video_id,
        name: file.name,
        type: file.type,
        size: file.size,
        lastModified: file.lastModified
      }))

      let currentProgress = 0
      const interval = setInterval(() => {
        currentProgress += currentProgress < 90 ? 10 : 2
        setProgress(currentProgress)
        if (currentProgress >= 100) {
          clearInterval(interval)
          setUploading(false)
          router.push('/dashboard')
        }
      }, 200)

    } catch (error: any) {
      setUploading(false)
      setError(error.message || 'Failed to upload video')
      setProgress(0)
      toast({
        variant: "destructive",
        title: "Upload failed",
        description: error.message || "Please try again"
      })
    }
  }

  useEffect(() => {
    return () => {
      if (videoUrl) {
        URL.revokeObjectURL(videoUrl)
      }
    }
  }, [videoUrl])

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-4rem)]">
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="text-center mb-12"
      >
        <h1 className="text-4xl md:text-6xl font-extrabold mb-4 gradient-text">
          Transform Your Videos with AI
        </h1>
        <p className="text-xl text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
          Generate professional subtitles in minutes using cutting-edge AI technology
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6 text-center"
      >
        {[
          { title: "AI-Powered", description: "Cutting-edge language processing" },
          { title: "Multi-Language", description: "Support for 99+ languages" },
          { title: "Lightning Fast", description: "Results in minutes, not hours" }
        ].map((feature, index) => (
          <Card key={index} className="bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border-none shadow-lg hover:shadow-xl transition-shadow">
            <CardContent className="p-6">
              <h3 className="text-xl font-semibold text-gray-800 dark:text-gray-200 mb-2">
                {feature.title}
              </h3>
              <p className="text-gray-600 dark:text-gray-400">
                {feature.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.6 }}
        className="mt-12"
      >
        <Button 
          size="lg"
          className="bg-blue-600 hover:bg-blue-700 text-white dark:bg-blue-500 dark:hover:bg-blue-400 dark:text-gray-900"
          onClick={() => router.push('/signup')}
        >
          Get Started Now
          <ArrowRight className="ml-2 h-5 w-5" />
        </Button>
      </motion.div>
    </div>
  )
}