"use client"

import type React from "react"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { ChefHat } from "lucide-react"

export default function LoginPage() {
  const [businessId, setBusinessId] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const router = useRouter()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!businessId.trim()) return

    setIsLoading(true)
    // Store business ID in localStorage for the dashboard
    localStorage.setItem("business_id", businessId.trim())

    // Simulate loading
    await new Promise((resolve) => setTimeout(resolve, 500))

    router.push("/dashboard")
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-red-50 flex items-center justify-center p-4">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader className="text-center space-y-4">
          <div className="mx-auto w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center">
            <ChefHat className="w-6 h-6 text-orange-600" />
          </div>
          <div>
            <CardTitle className="text-2xl font-bold text-gray-900">Restaurant Analytics</CardTitle>
            <CardDescription className="text-gray-600">Enter your business ID to access your dashboard</CardDescription>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleLogin} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="businessId">Business ID</Label>
              <Input
                id="businessId"
                type="text"
                placeholder="Enter your business ID"
                value={businessId}
                onChange={(e) => setBusinessId(e.target.value)}
                required
                className="w-full"
              />
            </div>
            <Button
              type="submit"
              className="w-full bg-orange-600 hover:bg-orange-700"
              disabled={isLoading || !businessId.trim()}
            >
              {isLoading ? "Logging in..." : "Login to Dashboard"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
