"use client"

import { useState, useEffect } from "react"
import type React from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"
import { TrendingUp, TrendingDown, DollarSign, ShoppingCart, LogOut, Calendar, Clock } from "lucide-react"

interface HistoricalData {
  date: string
  sales: number
  business_id: string
}

interface ForecastData {
  date: string
  predicted_sales: number
  lower_bound: number
  upper_bound: number
  business_id: string
}

interface ChartData {
  date: string
  sales?: number
  predicted_sales?: number
}

export default function DashboardPage() {
  const [businessId, setBusinessId] = useState<string>("")
  const [historicalData, setHistoricalData] = useState<HistoricalData[]>([])
  const [forecastData, setForecastData] = useState<ForecastData[]>([])
  const [chartData, setChartData] = useState<ChartData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string>("")
  const router = useRouter()

  // Overview states
  const [overview, setOverview] = useState<string>("")
  const [isOverviewLoading, setIsOverviewLoading] = useState<boolean>(false)
  const [overviewError, setOverviewError] = useState<string>("")

  // Escape HTML to prevent injection
  const escapeHtml = (unsafe: string) =>
    unsafe
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;")

  // Minimal inline markdown: **bold**, *italic*, __bold__, _italic_
  const formatInlineMarkdown = (text: string) => {
    const escaped = escapeHtml(text)
    const withBold = escaped.replace(/(\*\*|__)(.+?)\1/g, "<strong>$2</strong>")
    const withItalics = withBold.replace(/(?<!<strong>)(\*|_)(.+?)\1(?!<\/strong>)/g, "<em>$2</em>")
    return withItalics
  }

  // Nicely format the AI overview: paragraphs + bullet lists
  const renderOverview = (text: string) => {
    const lines = text.split(/\r?\n/)

    const elements: React.ReactNode[] = []
    let paragraphBuffer: string[] = []
    let bullets: string[] = []
    let keyCounter = 0

    const flushParagraph = () => {
      if (paragraphBuffer.length) {
        const html = formatInlineMarkdown(paragraphBuffer.join(" "))
        elements.push(
          <p key={`p-${keyCounter++}`} className="text-gray-700 leading-relaxed" dangerouslySetInnerHTML={{ __html: html }} />
        )
        paragraphBuffer = []
      }
    }

    const flushBullets = () => {
      if (bullets.length) {
        elements.push(
          <ul key={`ul-${keyCounter++}`} className="list-disc pl-5 space-y-1 text-gray-700">
            {bullets.map((b, i) => {
              const html = formatInlineMarkdown(b)
              return <li key={`li-${keyCounter}-${i}`} dangerouslySetInnerHTML={{ __html: html }} />
            })}
          </ul>
        )
        bullets = []
      }
    }

    lines.forEach((raw) => {
      const line = raw.trim()
      if (!line) {
        // blank line separates blocks
        flushBullets()
        flushParagraph()
        return
      }

      // bullet formats: -, *, •, or numbered like "1. "
      if (/^[-*•]\s+/.test(line)) {
        flushParagraph()
        bullets.push(line.replace(/^[-*•]\s+/, ""))
      } else if (/^\d+\.\s+/.test(line)) {
        flushParagraph()
        bullets.push(line.replace(/^\d+\.\s+/, ""))
      } else {
        flushBullets()
        paragraphBuffer.push(line)
      }
    })

    // flush any remaining content
    flushBullets()
    flushParagraph()

    return <div className="space-y-2">{elements}</div>
  }

  useEffect(() => {
    const storedBusinessId = localStorage.getItem("business_id")
    if (!storedBusinessId) {
      router.push("/")
      return
    }
    setBusinessId(storedBusinessId)
    fetchData(storedBusinessId)
    fetchOverview(storedBusinessId)
  }, [router])

  const fetchData = async (id: string) => {
    setIsLoading(true)
    setError("")

    try {
      const [historicalResponse, forecastResponse] = await Promise.all([
        fetch(`http://127.0.0.1:8000/api/sales/${id}/input`),
        fetch(`http://127.0.0.1:8000/api/sales/${id}/forecast`),
      ])

      if (!historicalResponse.ok || !forecastResponse.ok) {
        throw new Error("Failed to fetch data")
      }

      const historical: HistoricalData[] = await historicalResponse.json()
      const forecast: ForecastData[] = await forecastResponse.json()

      setHistoricalData(historical)
      setForecastData(forecast)

      const combinedData: ChartData[] = []

      // Add historical data
      historical.forEach((item) => {
        combinedData.push({
          date: item.date,
          sales: item.sales,
        })
      })

      // Add forecast data
      forecast.forEach((item) => {
        const existingIndex = combinedData.findIndex((d) => d.date === item.date)
        if (existingIndex >= 0) {
          combinedData[existingIndex].predicted_sales = item.predicted_sales
        } else {
          combinedData.push({
            date: item.date,
            predicted_sales: item.predicted_sales,
          })
        }
      })

      // Sort by date
      combinedData.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

      const lastHistoricalIndex = combinedData.findLastIndex((item) => item.sales !== undefined)
      const firstForecastIndex = combinedData.findIndex((item) => item.predicted_sales !== undefined)

      if (lastHistoricalIndex >= 0 && firstForecastIndex >= 0 && firstForecastIndex > lastHistoricalIndex + 1) {
        // There's a gap - insert a connecting point
        const lastHistoricalPoint = combinedData[lastHistoricalIndex]
        const firstForecastPoint = combinedData[firstForecastIndex]

        // Create a connecting point at the last historical date with both values
        if (lastHistoricalPoint && firstForecastPoint) {
          lastHistoricalPoint.predicted_sales = lastHistoricalPoint.sales
        }
      } else if (
        lastHistoricalIndex >= 0 &&
        firstForecastIndex >= 0 &&
        firstForecastIndex === lastHistoricalIndex + 1
      ) {
        // Adjacent points - add connecting value to the last historical point
        const lastHistoricalPoint = combinedData[lastHistoricalIndex]
        if (lastHistoricalPoint) {
          lastHistoricalPoint.predicted_sales = lastHistoricalPoint.sales
        }
      } else if (lastHistoricalIndex >= 0 && firstForecastIndex >= 0 && firstForecastIndex <= lastHistoricalIndex) {
        // Overlapping data - ensure smooth transition at the overlap point
        for (let i = firstForecastIndex; i <= lastHistoricalIndex; i++) {
          if (combinedData[i].sales !== undefined) {
            combinedData[i].predicted_sales = combinedData[i].sales
          }
        }
      }

      setChartData(combinedData)
    } catch (err) {
      setError("Failed to load dashboard data. Please check your connection.")
      console.error("Error fetching data:", err)
    } finally {
      setIsLoading(false)
    }
  }

  // Fetch overview from backend (does not block the main dashboard)
  const fetchOverview = async (id: string) => {
    setIsOverviewLoading(true)
    setOverviewError("")
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/sales/${id}/overview`)
      if (!res.ok) {
        throw new Error("Failed to fetch overview")
      }
      const data: { business_id: string; overview: string } = await res.json()
      setOverview(data.overview)
    } catch (e) {
      setOverview("")
      setOverviewError("Unable to load AI overview.")
      console.error("Error fetching overview:", e)
    } finally {
      setIsOverviewLoading(false)
    }
  }

  const handleLogout = () => {
    localStorage.removeItem("business_id")
    router.push("/")
  }

  // Calculate KPIs
  const totalSales = historicalData.reduce((sum, item) => sum + item.sales, 0)
  const avgDailySales = historicalData.length > 0 ? totalSales / historicalData.length : 0
  const forecastedSales = forecastData.reduce((sum, item) => sum + item.predicted_sales, 0)
  const growthRate =
    historicalData.length > 1
      ? ((historicalData[historicalData.length - 1]?.sales - historicalData[0]?.sales) / historicalData[0]?.sales) * 100
      : 0

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center">
                <DollarSign className="w-5 h-5 text-orange-600" />
              </div>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">Analytics</h1>
                <p className="text-sm text-gray-500">Business ID: {businessId}</p>
              </div>
            </div>
            <Button variant="outline" onClick={handleLogout} className="flex items-center space-x-2 bg-transparent">
              <LogOut className="w-4 h-4" />
              <span>Logout</span>
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800">{error}</p>
            <Button onClick={() => fetchData(businessId)} className="mt-2 bg-red-600 hover:bg-red-700" size="sm">
              Retry
            </Button>
          </div>
        )}

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Sales</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${totalSales.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">{historicalData.length} weeks of data</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Daily Sales</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${avgDailySales.toFixed(0)}</div>
              <p className="text-xs text-muted-foreground">Per day average</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Growth Rate</CardTitle>
              {growthRate >= 0 ? (
                <TrendingUp className="h-4 w-4 text-green-600" />
              ) : (
                <TrendingDown className="h-4 w-4 text-red-600" />
              )}
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${growthRate >= 0 ? "text-green-600" : "text-red-600"}`}>
                {growthRate >= 0 ? "+" : ""}
                {growthRate.toFixed(1)}%
              </div>
              <p className="text-xs text-muted-foreground">Period over period</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Forecasted Sales</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">${forecastedSales.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">{forecastData.length} weeks forecast</p>
            </CardContent>
          </Card>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* Sales Chart */}
          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle>Sales Trend & Forecast</CardTitle>
              <CardDescription>Historical sales data with AI-powered forecasting</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="1 1" stroke="#f1f5f9" strokeOpacity={0.5} />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: "#64748b" }}
                      tickLine={{ stroke: "#e2e8f0" }}
                      axisLine={{ stroke: "#e2e8f0" }}
                      interval="preserveStartEnd"
                      tickFormatter={(value) => {
                        const date = new Date(value)
                        return date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
                      }}
                      minTickGap={30}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: "#64748b" }}
                      tickLine={{ stroke: "#e2e8f0" }}
                      axisLine={{ stroke: "#e2e8f0" }}
                      tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "white",
                        border: "1px solid #e2e8f0",
                        borderRadius: "8px",
                        boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                        fontSize: "12px",
                      }}
                      labelStyle={{ color: "#374151", fontWeight: "600" }}
                      labelFormatter={(value) =>
                        new Date(value).toLocaleDateString("en-US", {
                          weekday: "short",
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })
                      }
                      formatter={(value: number, name: string) => [
                        `$${value?.toLocaleString()}`,
                        name === "sales" ? "Historical Sales" : name === "predicted_sales" ? "Forecasted Sales" : name,
                      ]}
                    />
                    <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "20px" }} iconType="line" />
                    <Line
                      type="monotone"
                      dataKey="sales"
                      stroke="#ea580c"
                      strokeWidth={2.5}
                      name="Historical Sales"
                      connectNulls={false}
                      dot={false}
                      activeDot={{ r: 5, stroke: "#ea580c", strokeWidth: 2, fill: "white" }}
                    />
                    <Line
                      type="monotone"
                      dataKey="predicted_sales"
                      stroke="#3b82f6"
                      strokeWidth={2.5}
                      strokeDasharray="5 5"
                      name="Forecasted Sales"
                      connectNulls={false}
                      dot={false}
                      activeDot={{ r: 5, stroke: "#3b82f6", strokeWidth: 2, fill: "white" }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Trend Overview */}
          <Card>
            <CardHeader>
              <CardTitle>Trend Overview</CardTitle>
            </CardHeader>
            <CardContent className="py-4">
              {isOverviewLoading ? (
                <CardDescription className="text-center">Analyzing trends...</CardDescription>
              ) : overviewError ? (
                <CardDescription className="text-center">{overviewError}</CardDescription>
              ) : overview ? (
                <div className="text-sm">{renderOverview(overview)}</div>
              ) : (
                <CardDescription className="text-center">No overview available</CardDescription>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Bottom Section */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Orders */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <ShoppingCart className="w-5 h-5" />
                <span>Recent Orders</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="font-medium">#1234</p>
                  <p className="text-sm text-muted-foreground">John Smith • $24.50</p>
                </div>
                <Badge variant="secondary" className="bg-green-100 text-green-800">
                  Completed
                </Badge>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="font-medium">#1235</p>
                  <p className="text-sm text-muted-foreground">Sarah Johnson • $18.75</p>
                </div>
                <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                  Preparing
                </Badge>
              </div>
              <div className="flex items-center space-x-3">
                <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="font-medium">#1236</p>
                  <p className="text-sm text-muted-foreground">Mike Davis • $32.25</p>
                </div>
                <Badge variant="secondary" className="bg-yellow-100 text-yellow-800">
                  New
                </Badge>
              </div>
            </CardContent>
          </Card>

          {/* Order Sources */}
          <Card>
            <CardHeader>
              <CardTitle>Order Sources</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">Dine-in</span>
                <div className="flex items-center space-x-2">
                  <div className="w-20 h-2 bg-gray-200 rounded-full">
                    <div className="w-3/5 h-2 bg-orange-500 rounded-full"></div>
                  </div>
                  <span className="text-sm font-medium">60%</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Takeout</span>
                <div className="flex items-center space-x-2">
                  <div className="w-20 h-2 bg-gray-200 rounded-full">
                    <div className="w-1/4 h-2 bg-blue-500 rounded-full"></div>
                  </div>
                  <span className="text-sm font-medium">25%</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Delivery</span>
                <div className="flex items-center space-x-2">
                  <div className="w-20 h-2 bg-gray-200 rounded-full">
                    <div className="w-3/20 h-2 bg-green-500 rounded-full"></div>
                  </div>
                  <span className="text-sm font-medium">15%</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Performance Metrics */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Clock className="w-5 h-5" />
                <span>Performance</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm">Avg Order Time</span>
                <span className="text-sm font-medium">12 min</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Customer Rating</span>
                <div className="flex items-center space-x-1">
                  <span className="w-4 h-4 rounded-full bg-yellow-400 inline-block" />
                  <span className="text-sm font-medium">4.8</span>
                </div>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Orders Today</span>
                <span className="text-sm font-medium">47</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Revenue Today</span>
                <span className="text-sm font-medium">$1,247</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
