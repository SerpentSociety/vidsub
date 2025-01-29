import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://127.0.0.1:5000/api'

axios.defaults.withCredentials = true
axios.defaults.headers.common['Accept'] = 'application/json'

export interface SubtitleSegment {
    start: number
    end: number
    text: string
}

interface VideoUploadResponse {
    video_id: string
    filename: string
    message: string
}

interface ProcessingStatus {
    status: 'uploaded' | 'processing' | 'completed' | 'failed'
    progress: number
    error?: string
    transcription?: string
    detected_language?: string
    output_path?: string
    segments?: SubtitleSegment[]
}

export class VideoService {
    static async uploadVideo(file: File): Promise<VideoUploadResponse> {
        const formData = new FormData()
        formData.append('video', file)
        const token = localStorage.getItem('authToken')

        try {
            const response = await axios.post(`${API_URL}/video/upload`, formData, {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'multipart/form-data',
                },
                withCredentials: true
            })
            return response.data
        } catch (error: any) {
            throw new Error(error.response?.data?.error || 'Failed to upload video')
        }
    }

    static async startProcessing(videoId: string, targetLanguage: string, fontSize: number): Promise<void> {
        const token = localStorage.getItem('authToken')
        try {
            await axios.post(
                `${API_URL}/video/process`,
                {
                    video_id: videoId,
                    target_language: targetLanguage,
                    font_size: fontSize
                },
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    withCredentials: true
                }
            )
        } catch (error: any) {
            throw new Error(error.response?.data?.error || 'Failed to start processing')
        }
    }

    static getProcessingStream(videoId: string, targetLanguage: string, fontSize: number): EventSource {
        const params = new URLSearchParams({
            video_id: videoId,
            target_language: targetLanguage,
            font_size: fontSize.toString(),
            token: localStorage.getItem('authToken') || ''
        })

        const eventSource = new EventSource(
            `${API_URL}/video/process?${params.toString()}`,
            { withCredentials: true }
        )

        eventSource.onerror = (error) => {
            console.error("Processing EventSource failed:", error)
            eventSource.close()
        }

        return eventSource
    }

    static getDownloadUrl(videoId: string): string {
        const token = localStorage.getItem('authToken')
        return `${API_URL}/video/download/${videoId}?token=${token}`
    }

    static async getStatus(videoId: string): Promise<ProcessingStatus> {
        const token = localStorage.getItem('authToken')
        try {
            const response = await axios.get(`${API_URL}/video/status/${videoId}`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                },
                withCredentials: true
            })
            return response.data
        } catch (error: any) {
            throw new Error(error.response?.data?.error || 'Failed to get video status')
        }
    }

    static async updateSubtitles(videoId: string, segments: SubtitleSegment[]): Promise<void> {
        const token = localStorage.getItem('authToken')
        try {
            await axios.post(
                `${API_URL}/video/update_subtitles/${videoId}`,
                { segments },
                {
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    withCredentials: true
                }
            )
        } catch (error: any) {
            throw new Error(error.response?.data?.error || 'Failed to update subtitles')
        }
    }
    
    static regenerateVideo(
        videoId: string, 
        segments: SubtitleSegment[],
        fontSize: number,
        targetLanguage: string
    ): EventSource {
        const token = localStorage.getItem('authToken')
        const params = new URLSearchParams({
            segments: JSON.stringify(segments),
            font_size: fontSize.toString(),
            target_language: targetLanguage,
            token: token || ''
        })

        const eventSource = new EventSource(
            `${API_URL}/video/regenerate/${videoId}?${params.toString()}`,
            { 
                withCredentials: true 
            }
        )

        eventSource.onerror = (error) => {
            console.error("Regeneration EventSource failed:", error)
            eventSource.close()
        }

        return eventSource
    }
}