'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2, Download, Play, Upload, AlertCircle, Save } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { VideoService } from '@/lib/services/video'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { 
  SUPPORTED_LANGUAGES, 
  getFontSizes,
  getDefaultFontSize,
  type FontSize,
  type LanguageCode 
} from '@/lib/constants/languages'
import { useVideo } from '@/hooks/useVideo'
import type { SubtitleSegment } from '@/lib/services/video'

const formatTimestamp = (seconds: number) => {
  const date = new Date(seconds * 1000)
  return date.toISOString().substr(11, 8).replace(/^00:/, '').replace(/^0/, '')
}

export default function Dashboard() {
  const [file, setFile] = useState<File | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [targetLanguage, setTargetLanguage] = useState('en')
  const [isPortrait, setIsPortrait] = useState(false)
  const [fontSize, setFontSize] = useState<FontSize>(getDefaultFontSize(false))
  const [detectedLanguage, setDetectedLanguage] = useState<string | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [videoKey, setVideoKey] = useState(0)
  const [segments, setSegments] = useState<SubtitleSegment[]>([])
  const [editedSegments, setEditedSegments] = useState<SubtitleSegment[]>([])
  const [fakeProgress, setFakeProgress] = useState(0)
  const [isProgressCompleted, setIsProgressCompleted] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const editTimeoutRef = useRef<NodeJS.Timeout>()
  const progressIntervalRef = useRef<NodeJS.Timeout>()
  const progressStartTimeRef = useRef<number | null>(null)

  const { toast } = useToast()
  const { state, processVideo, regenerateVideo, resetState } = useVideo()

  const isRTL = SUPPORTED_LANGUAGES.find(l => l.code === targetLanguage)?.rtl || false

  // Fake progress simulation
  const startFakeProgress = useCallback(() => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current)
    }

    setFakeProgress(0)
    setIsProgressCompleted(false)
    progressStartTimeRef.current = Date.now()
    
    progressIntervalRef.current = setInterval(() => {
      const elapsedTime = Date.now() - (progressStartTimeRef.current || 0)
      
      setFakeProgress(prev => {
        // Slow progress for first 15 seconds
        if (elapsedTime < 15000) {
          const slowIncrement = Math.random() * 3
          return Math.min(prev + slowIncrement, 35)
        }
        
        // Faster progress after 15 seconds, but not reaching 100
        const fastIncrement = Math.random() * 5
        return Math.min(prev + fastIncrement, 95)
      })
    }, 500)
  }, [])

  const stopFakeProgress = useCallback(() => {
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current)
    }
    setIsProgressCompleted(true)
  }, [])

  useEffect(() => {
    return () => {
      if (videoUrl) URL.revokeObjectURL(videoUrl)
      if (editTimeoutRef.current) {
        clearTimeout(editTimeoutRef.current)
      }
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current)
      }
    }
  }, [videoUrl])

  useEffect(() => {
    if (state.detected_language) {
      setDetectedLanguage(state.detected_language)
    }

    if (state.segments) {
      setSegments(state.segments)
    }

    if (state.status === 'completed' && state.downloadUrl) {
      setIsProcessing(false)
      setIsRegenerating(false)
      stopFakeProgress()
      
      // Force a final state check
      if (state.videoId) {
        VideoService.getStatus(state.videoId)
          .then(status => {
            if (status.output_path) {
              setVideoKey(prev => prev + 1)
            }
          })
          .catch(console.error)
      }
    }
  }, [state, stopFakeProgress])

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return

    const selectedFile = e.target.files[0]
    if (selectedFile.size > 500 * 1024 * 1024) {
      toast({
        variant: "destructive",
        title: "File too large",
        description: "Maximum file size is 500MB"
      })
      return
    }

    setFile(selectedFile)
    setVideoUrl(URL.createObjectURL(selectedFile))
    setVideoKey(prev => prev + 1)
    resetState()
    setSegments([])
    setEditedSegments([])
    setIsProgressCompleted(false)
  }, [resetState, toast])

  const checkVideoOrientation = useCallback((width: number, height: number) => {
    const portrait = height > width
    setIsPortrait(portrait)
    setFontSize(getDefaultFontSize(portrait))
  }, [])

  const handleVideoLoaded = useCallback((e: React.SyntheticEvent<HTMLVideoElement>) => {
    const video = e.currentTarget
    checkVideoOrientation(video.videoWidth, video.videoHeight)
  }, [checkVideoOrientation])

  const handleStartProcessing = useCallback(async () => {
    if (!file || isProcessing) return
    setIsProcessing(true)
    startFakeProgress()
    
    try {
      // Start processing and set up status polling
      const processPromise = processVideo(file, targetLanguage, parseInt(fontSize))

      // Set up status polling
      const pollStatus = async () => {
        if (!state.videoId) return
        try {
          const status = await VideoService.getStatus(state.videoId)
          if (status.output_path) {
            setVideoKey(prev => prev + 1)
          }
        } catch (error) {
          console.error('Status check error:', error)
        }
      }

      // Start polling
      const pollInterval = setInterval(pollStatus, 2000)

      // Wait for processing to complete
      await processPromise

      // Clean up polling
      clearInterval(pollInterval)
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Processing Failed",
        description: error.message || "An error occurred during processing"
      })
    } finally {
      setIsProcessing(false)
    }
  }, [file, targetLanguage, fontSize, processVideo, toast, state.videoId, startFakeProgress])

  const handleSegmentEdit = useCallback((index: number, newText: string) => {
    const newEditedSegments = [...(editedSegments.length > 0 ? editedSegments : segments)];
    newEditedSegments[index] = {
      ...newEditedSegments[index],
      text: newText
    };
    setEditedSegments(newEditedSegments);
  }, [editedSegments, segments])

  const handleSaveChanges = useCallback(async () => {
    if (!state.videoId) return
    
    setIsRegenerating(true)
    startFakeProgress()
    try {
      const eventSource = VideoService.regenerateVideo(
        state.videoId,
        editedSegments,
        parseInt(fontSize),
        targetLanguage
      )

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.error) {
            toast({
              variant: "destructive",
              title: "Regeneration Failed",
              description: data.error
            })
            eventSource.close()
            setIsRegenerating(false)
            stopFakeProgress()
            return
          }

          // Handle completion
          if (data.progress === 100 && data.output_path) {
            // Update segments if provided
            if (data.segments) {
              setSegments(data.segments)
              setEditedSegments([])
            }
            
            // Force video reload
            setVideoKey(prev => prev + 1)
            
            // Close connection and reset regeneration state
            eventSource.close()
            setIsRegenerating(false)
            stopFakeProgress()
            
            // Force a status check to update the video state
            VideoService.getStatus(state.videoId!).then(status => {
              if (status.output_path) {
                setVideoKey(prev => prev + 1)
              }
            }).catch(error => {
              console.error('Status check error:', error)
            })
          }
        } catch (error) {
          console.error('Error parsing SSE data:', error)
          eventSource.close()
          setIsRegenerating(false)
          stopFakeProgress()
          toast({
            variant: "destructive",
            title: "Regeneration Failed",
            description: "Failed to process server response"
          })
        }
      }

      eventSource.onerror = (error) => {
        console.error('Regeneration SSE error:', error)
        eventSource.close()
        setIsRegenerating(false)
        stopFakeProgress()
        toast({
          variant: "destructive",
          title: "Regeneration Failed",
          description: "Connection lost"
        })
      }

    } catch (error: any) {
      setIsRegenerating(false)
      stopFakeProgress()
      toast({
        variant: "destructive",
        title: "Regeneration Failed",
        description: error.message || "Failed to update subtitles"
      })
    }
  }, [
    state.videoId, 
    editedSegments, 
    fontSize, 
    targetLanguage, 
    toast, 
    startFakeProgress, 
    stopFakeProgress
  ])

  const handleDownload = useCallback(() => {
    if (!state.downloadUrl) return
    
    const a = document.createElement('a')
    a.href = state.downloadUrl
    a.download = `subtitled_video_${targetLanguage}.mp4`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  }, [state.downloadUrl, targetLanguage])

  return (
    <div className="flex flex-col min-h-screen">
      <main className="flex-grow">
        <div className="container px-4 py-8">
          <motion.div 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-8"
          >
            <Card>
              <CardHeader>
                <CardTitle>Video Selection</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="space-y-2">
                    <Label>Target Language</Label>
                    <Select 
                      value={targetLanguage} 
                      onValueChange={setTargetLanguage}
                      disabled={isProcessing || isRegenerating}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select language" />
                      </SelectTrigger>
                      <SelectContent>
                        {SUPPORTED_LANGUAGES.map(lang => (
                          <SelectItem key={lang.code} value={lang.code}>
                            {lang.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Font Size</Label>
                    <Select
                      value={fontSize}
                      onValueChange={(value) => setFontSize(value as FontSize)}
                      disabled={isProcessing || isRegenerating}
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Select size" />
                      </SelectTrigger>
                      <SelectContent>
                        {getFontSizes(isPortrait).map(size => (
                          <SelectItem key={size.value} value={size.value}>
                            {size.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-4">
                  <Input
                    id="video-upload"
                    type="file"
                    accept="video/*"
                    className="hidden"
                    onChange={handleFileChange}
                    disabled={isProcessing || isRegenerating}
                  />
                  
                  {!file ? (
                    <Button 
                      onClick={() => document.getElementById('video-upload')?.click()}
                      className="w-full"
                      disabled={isProcessing || isRegenerating}
                    >
                      <Upload className="mr-2 h-4 w-4" />
                      Select Video
                    </Button>
                  ) : (
                    <div className="space-y-4">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {videoUrl && (
                          <div>
                            <Label className="mb-2 block">Input Video</Label>
                            <video 
                              ref={videoRef}
                              key={`input-${videoKey}`}
                              src={videoUrl} 
                              controls 
                              className="w-full rounded-lg aspect-video bg-black"
                              onLoadedMetadata={handleVideoLoaded}
                            />
                          </div>
                        )}
                        {state.downloadUrl && (
                          <div>
                            <Label className="mb-2 block">Output Video</Label>
                            <video 
                              key={`output-${videoKey}`}
                              src={state.downloadUrl} 
                              controls 
                              className="w-full rounded-lg aspect-video bg-black"
                              onLoadedMetadata={handleVideoLoaded}
                            />
                          </div>
                        )}
                      </div>

                      {(isProcessing || isRegenerating) && (
                        <Card>
                          <CardHeader>
                            <CardTitle>Processing Video</CardTitle>
                          </CardHeader>
                          <CardContent>
                            {!isProgressCompleted ? (
                              <Progress value={fakeProgress} />
                            ) : (
                              <div className="text-center font-semibold text-green-600">
                                Completed
                              </div>
                            )}
                          </CardContent>
                        </Card>
                      )}

                      {detectedLanguage && (
                        <Alert>
                        <AlertDescription>
                          Detected language: {
                            SUPPORTED_LANGUAGES.find(l => l.code === detectedLanguage)?.name || 
                            detectedLanguage
                          }
                        </AlertDescription>
                      </Alert>
                    )}

                    <div className="flex gap-4">
                      {!state.downloadUrl && (
                        <Button
                          onClick={handleStartProcessing}
                          className="flex-1"
                          disabled={isProcessing || isRegenerating}
                        >
                          {isProcessing ? (
                            <>
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                              Processing...
                            </>
                          ) : (
                            <>
                              <Play className="mr-2 h-4 w-4" />
                              Start Processing
                            </>
                          )}
                        </Button>
                      )}

                      {state.downloadUrl && (
                        <Button
                          variant="outline"
                          onClick={handleDownload}
                          disabled={isProcessing || isRegenerating}
                        >
                          <Download className="mr-2 h-4 w-4" />
                          Download
                        </Button>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {state.error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>{state.error}</AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          {segments.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Generated Subtitles</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-4 max-h-[500px] overflow-y-auto pr-4">
                  {segments.map((segment, index) => (
                    <div key={index} className="grid grid-cols-[120px_1fr] gap-4 items-start">
                      <div className="text-sm text-muted-foreground font-mono pt-2">
                        {formatTimestamp(segment.start)} → {formatTimestamp(segment.end)}
                      </div>
                      <Textarea
                        value={(editedSegments[index] || segment).text}
                        onChange={(e) => handleSegmentEdit(index, e.target.value)}
                        disabled={isProcessing || isRegenerating}
                        className="min-h-[80px]"
                        dir={isRTL ? 'rtl' : 'ltr'}
                        style={{
                          textAlign: isRTL ? 'right' : 'left',
                          direction: isRTL ? 'rtl' : 'ltr'
                        }}
                      />
                    </div>
                  ))}
                </div>
                {editedSegments.length > 0 && (
                  <Button
                    onClick={handleSaveChanges}
                    disabled={isProcessing || isRegenerating}
                    className="w-full"
                  >
                    <Save className="mr-2 h-4 w-4" />
                    Save Changes
                  </Button>
                )}
              </CardContent>
            </Card>
          )}
        </motion.div>
      </div>
    </main>
  </div>
)
}