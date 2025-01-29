import { Button } from "@/components/ui/button"
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Check } from 'lucide-react'

export default function PricingPage() {
  const plans = [
    {
      name: "Basic",
      price: "$9.99",
      features: [
        "5 hours of video processing per month",
        "AI-powered subtitle generation",
        "Export in 3 formats",
        "Email support"
      ]
    },
    {
      name: "Pro",
      price: "$24.99",
      features: [
        "20 hours of video processing per month",
        "AI-powered subtitle generation",
        "Translation to 10 languages",
        "Export in all formats",
        "Priority email support"
      ]
    },
    {
      name: "Enterprise",
      price: "Custom",
      features: [
        "Unlimited video processing",
        "AI-powered subtitle generation",
        "Translation to all supported languages",
        "Custom integrations",
        "Dedicated account manager"
      ]
    }
  ]

  return (
    <div className="container mx-auto px-4 py-16">
      <h1 className="text-4xl font-bold text-center mb-12 gradient-text">Pricing Plans</h1>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {plans.map((plan, index) => (
          <Card key={index} className="bg-white/80 dark:bg-gray-800/80 backdrop-blur-lg border-none shadow-lg hover:shadow-xl transition-shadow flex flex-col">
            <CardHeader>
              <CardTitle className="text-2xl font-bold text-center">{plan.name}</CardTitle>
            </CardHeader>
            <CardContent className="flex-grow">
              <p className="text-3xl font-bold text-center mb-6">{plan.price}</p>
              <ul className="space-y-2">
                {plan.features.map((feature, featureIndex) => (
                  <li key={featureIndex} className="flex items-center">
                    <Check className="mr-2 h-5 w-5 text-green-500" />
                    <span className="text-gray-600 dark:text-gray-300">{feature}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
            <CardFooter>
              <Button className="w-full" variant={index === 1 ? "default" : "outline"}>
                {index === 2 ? "Contact Sales" : "Choose Plan"}
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>
    </div>
  )
}

