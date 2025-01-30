import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Play } from 'lucide-react'

export default function FeaturesPage() {
  const demos = [
    {
      title: "Video Enhancement Demo",
      description: "Watch how our AI transforms low-quality videos into crystal clear content",
      videoId: "X7o8rPNsQNM"  // First YouTube video ID
    },
    {
      title: "Real-time Processing Demo",
      description: "See our lightning-fast processing in action",
      videoId: "kUf_2n1VKBc"  // Second YouTube video ID
    }
  ]

  return (
    <div className="container mx-auto px-4 py-16">
      <h1 className="text-4xl font-bold text-center mb-6 gradient-text">Experience the Magic</h1>
      
      <p className="text-center text-gray-600 dark:text-gray-300 mb-12 max-w-3xl mx-auto">
        Witness the power of our AI-driven video enhancement technology through these interactive demos. 
        From real-time processing to stunning quality improvements, see firsthand how we're revolutionizing video enhancement.
      </p>
      
      {/* Demo Videos Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {demos.map((demo, index) => (
          <Card key={index} className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-lg border-none shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center">
                <Play className="mr-2 h-5 w-5 text-blue-500" />
                {demo.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="aspect-video bg-gray-100 dark:bg-gray-700 rounded-lg overflow-hidden mb-4">
                <iframe
                  className="w-full h-full"
                  src={`https://www.youtube.com/embed/${demo.videoId}`}
                  title={demo.title}
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                ></iframe>
              </div>
              <p className="text-gray-600 dark:text-gray-300">{demo.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}