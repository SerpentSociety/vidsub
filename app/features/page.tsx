import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { CheckCircle } from 'lucide-react'

export default function FeaturesPage() {
  const features = [
    {
      title: "AI-Powered Subtitle Generation",
      description: "Automatically generate accurate subtitles using cutting-edge AI technology."
    },
    {
      title: "Multi-Language Support",
      description: "Translate subtitles into over 50 languages with a single click."
    },
    {
      title: "Real-Time Editing",
      description: "Edit and fine-tune your subtitles in real-time with our intuitive interface."
    },
    {
      title: "Custom Styling",
      description: "Customize the appearance of your subtitles to match your brand or preferences."
    },
    {
      title: "Automatic Syncing",
      description: "Our AI ensures that subtitles are perfectly synced with your video content."
    },
    {
      title: "Export in Multiple Formats",
      description: "Export your subtitles in various formats compatible with major video platforms."
    }
  ]

  return (
    <div className="container mx-auto px-4 py-16">
      <h1 className="text-4xl font-bold text-center mb-12 gradient-text">Features</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        {features.map((feature, index) => (
          <Card key={index} className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-lg border-none shadow-lg hover:shadow-xl transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center">
                <CheckCircle className="mr-2 h-5 w-5 text-green-500" />
                {feature.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600 dark:text-gray-300">{feature.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

