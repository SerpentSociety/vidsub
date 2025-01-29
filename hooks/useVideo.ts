import { useState, useEffect, useCallback, useRef } from 'react'
import { VideoService, type SubtitleSegment } from '@/lib/services/video'
import { useToast } from '@/hooks/use-toast'

interface VideoState {
  status: 'idle' | 'uploading' | 'processing' | 'completed' | 'error'
  progress: number
  error?: string
  videoId?: string
  downloadUrl?: string
  transcription?: string
  currentStep?: string
  detected_language?: string
  segments?: SubtitleSegment[]
}

export function useVideo() {
  const [state, setState] = useState<VideoState>({
    status: 'idle',
    progress: 0
  })
  
  const eventSourceRef = useRef<EventSource | null>(null)
  const videoCheckIntervalRef = useRef<NodeJS.Timeout | null>(null)
  const { toast } = useToast()
  const currentVideoIdRef = useRef<string | null>(null)
  const retryCountRef = useRef(0)
  const MAX_RETRIES = 3

  const closeEventSource = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
  }, [])

  const clearVideoCheckInterval = useCallback(() => {
    if (videoCheckIntervalRef.current) {
      clearInterval(videoCheckIntervalRef.current)
      videoCheckIntervalRef.current = null
    }
  }, [])

  const checkVideoStatus = useCallback(async () => {
    if (!currentVideoIdRef.current) return

    try {
      const status = await VideoService.getStatus(currentVideoIdRef.current)
      
      if (status.status === 'completed' && status.output_path) {
        const downloadUrl = VideoService.getDownloadUrl(currentVideoIdRef.current)
        setState(prev => ({
          ...prev,
          status: 'completed',
          progress: 100,
          downloadUrl,
          segments: status.segments || prev.segments
        }))
        clearVideoCheckInterval()
      } else if (status.status === 'failed') {
        setState(prev => ({
          ...prev,
          status: 'error',
          error: status.error || 'Processing failed'
        }))
        clearVideoCheckInterval()
      }
    } catch (error) {
      console.error('Failed to check video status:', error)
    }
  }, [clearVideoCheckInterval])

  const startVideoStatusCheck = useCallback(() => {
    clearVideoCheckInterval()
    videoCheckIntervalRef.current = setInterval(checkVideoStatus, 2000)
  }, [checkVideoStatus, clearVideoCheckInterval])

  const processVideo = useCallback(async (
    file: File, 
    targetLanguage: string, 
    fontSize: number
  ) => {
    closeEventSource()
    clearVideoCheckInterval()
    retryCountRef.current = 0

    try {
      setState(prev => ({ 
        ...prev,
        status: 'uploading', 
        progress: 0,
        error: undefined,
        downloadUrl: undefined,
        transcription: undefined,
        currentStep: undefined,
        videoId: undefined,
        detected_language: undefined,
        segments: undefined
      }))
      
      const uploadResult = await VideoService.uploadVideo(file)
      currentVideoIdRef.current = uploadResult.video_id
      
      setState(prev => ({ 
        ...prev,
        status: 'processing', 
        progress: 0,
        videoId: uploadResult.video_id 
      }))

      await VideoService.startProcessing(
        uploadResult.video_id,
        targetLanguage,
        fontSize
      )

      return new Promise<string>((resolve, reject) => {
        const connectEventSource = () => {
          const eventSource = VideoService.getProcessingStream(
            uploadResult.video_id,
            targetLanguage,
            fontSize
          )

          eventSourceRef.current = eventSource

          eventSource.onmessage = (event: MessageEvent) => {
            try {
              const data = JSON.parse(event.data)
              
              if (data.status === 'failed' || data.error) {
                closeEventSource()
                setState(prev => ({ 
                  ...prev, 
                  status: 'error', 
                  error: data.error || 'Processing failed'
                }))
                reject(data.error || 'Processing failed')
                return
              }

              setState(prev => ({
                ...prev,
                status: 'processing',
                progress: data.progress || prev.progress,
                currentStep: data.step || prev.currentStep,
                detected_language: data.detected_language || prev.detected_language,
                transcription: data.transcription || prev.transcription,
                segments: data.segments || prev.segments
              }))

              if (data.status === 'completed' && data.progress === 100 && data.output_path) {
                const downloadUrl = VideoService.getDownloadUrl(uploadResult.video_id)
                setState(prev => ({ 
                  ...prev, 
                  status: 'completed', 
                  progress: 100,
                  downloadUrl,
                  transcription: data.transcription || prev.transcription,
                  currentStep: 'Complete',
                  segments: data.segments || prev.segments
                }))
                closeEventSource()
                startVideoStatusCheck()
                resolve(downloadUrl)
              }

            } catch (error: any) {
              console.error('Error parsing SSE data:', error)
              if (retryCountRef.current < MAX_RETRIES) {
                retryCountRef.current++
                closeEventSource()
                setTimeout(connectEventSource, 1000)
              } else {
                closeEventSource()
                setState(prev => ({
                  ...prev,
                  status: 'error',
                  error: 'Failed to process video'
                }))
                reject('Failed to process video')
              }
            }
          }

          eventSource.onerror = (error: Event) => {
            console.error('SSE Connection error:', error)
            if (retryCountRef.current < MAX_RETRIES) {
              retryCountRef.current++
              closeEventSource()
              setTimeout(connectEventSource, 1000)
            } else {
              closeEventSource()
              setState(prev => ({ 
                ...prev,
                status: 'error', 
                error: 'Connection lost' 
              }))
              reject('Connection lost')
            }
          }

          eventSource.onopen = () => {
            retryCountRef.current = 0
          }
        }

        connectEventSource()
      })

    } catch (error: any) {
      closeEventSource()
      clearVideoCheckInterval()
      setState(prev => ({ 
        ...prev,
        status: 'error', 
        error: error.message || 'An unexpected error occurred' 
      }))
      throw error
    }
  }, [closeEventSource, clearVideoCheckInterval, startVideoStatusCheck])

  const regenerateVideo = useCallback(async (
    videoId: string,
    segments: SubtitleSegment[],
    fontSize: number,
    targetLanguage: string
  ) => {
    closeEventSource()
    clearVideoCheckInterval()
    retryCountRef.current = 0

    try {
      setState(prev => ({
        ...prev,
        status: 'processing',
        progress: 0,
        error: undefined
      }))

      return new Promise<string>((resolve, reject) => {
        const eventSource = VideoService.regenerateVideo(
          videoId, 
          segments, 
          fontSize, 
          targetLanguage
        )
        eventSourceRef.current = eventSource

        eventSource.onmessage = (event: MessageEvent) => {
          try {
            const data = JSON.parse(event.data)
            
            if (data.error) {
              closeEventSource()
              setState(prev => ({
                ...prev,
                status: 'error',
                error: data.error
              }))
              reject(data.error)
              return
            }

            setState(prev => ({
              ...prev,
              status: 'processing',
              progress: data.progress || prev.progress,
              currentStep: data.step || prev.currentStep
            }))

            if (data.progress === 100 && data.output_path) {
              const downloadUrl = VideoService.getDownloadUrl(videoId)
              setState(prev => ({
                ...prev,
                status: 'completed',
                progress: 100,
                downloadUrl,
                segments: data.segments || prev.segments
              }))
              closeEventSource()
              startVideoStatusCheck()
              resolve(downloadUrl)
            }
          } catch (error) {
            console.error('Regeneration error:', error)
            closeEventSource()
            reject('Failed to parse regeneration data')
          }
        }

        eventSource.onerror = (error) => {
          console.error('Regeneration SSE error:', error)
          closeEventSource()
          setState(prev => ({
            ...prev,
            status: 'error',
            error: 'Regeneration connection failed'
          }))
          reject('Connection failed during regeneration')
        }
      })
    } catch (error: any) {
      closeEventSource()
      setState(prev => ({
        ...prev,
        status: 'error',
        error: error.message || 'Regeneration failed'
      }))
      throw error
    }
  }, [closeEventSource, clearVideoCheckInterval, startVideoStatusCheck])

  const resetState = useCallback(() => {
    closeEventSource()
    clearVideoCheckInterval()
    setState({
      status: 'idle',
      progress: 0
    })
    currentVideoIdRef.current = null
    retryCountRef.current = 0
  }, [closeEventSource, clearVideoCheckInterval])

  useEffect(() => {
    if (state.status === 'completed' && !state.downloadUrl && currentVideoIdRef.current) {
      startVideoStatusCheck()
    }
  }, [state.status, state.downloadUrl, startVideoStatusCheck])

  useEffect(() => {
    return () => {
      closeEventSource()
      clearVideoCheckInterval()
    }
  }, [closeEventSource, clearVideoCheckInterval])

  return {
    state,
    processVideo,
    regenerateVideo,
    resetState
  }
}