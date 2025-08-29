"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts"
import { TrendingUp, TrendingDown, DollarSign, ShoppingCart, Star, LogOut, Calendar, Clock } from "lucide-react"

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
  historical?: number
  forecast?: number
}

export default function DashboardPage() {
  const [businessId, setBusinessId] = useState<string>("")
  const [historicalData, setHistoricalData] = useState<HistoricalData[]>([])
  const [forecastData, setForecastData] = useState<ForecastData[]>([])
  const [chartData, setChartData] = useState<ChartData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string>("")
  const router = useRouter()

  useEffect(() => {
    const storedBusinessId = localStorage.getItem("business_id")
    if (!storedBusinessId) {
      router.push("/")
      return
    }
    setBusinessId(storedBusinessId)
    fetchData(storedBusinessId)
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

      // Combine data for chart
      const combinedData: ChartData[] = []

      // Add historical data
      historical.forEach((item) => {
        combinedData.push({
          date: item.date,
          historical: item.sales,
        })
      })

      // Add forecast data
      forecast.forEach((item) => {
        const existingIndex = combinedData.findIndex((d) => d.date === item.date)
        if (existingIndex >= 0) {
          combinedData[existingIndex].forecast = item.predicted_sales
        } else {
          combinedData.push({
            date: item.date,
            forecast: item.predicted_sales,
          })
        }
      })

      // Sort by date
      combinedData.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())
      setChartData(combinedData)
    } catch (err) {
      setError("Failed to load dashboard data. Please check your connection.")
      console.error("Error fetching data:", err)
    } finally {
      setIsLoading(false)
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
                <h1 className="text-xl font-semibold text-gray-900">Restaurant Analytics</h1>
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
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
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
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12 }}
                      tickFormatter={(value) => new Date(value).toLocaleDateString()}
                    />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip
                      labelFormatter={(value) => new Date(value).toLocaleDateString()}
                      formatter={(value: number, name: string) => [
                        `$${value?.toLocaleString()}`,
                        name === "historical" ? "Historical Sales" : "Forecasted Sales",
                      ]}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="historical"
                      stroke="#ea580c"
                      strokeWidth={2}
                      name="Historical Sales"
                      connectNulls={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="forecast"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      strokeDasharray="5 5"
                      name="Forecasted Sales"
                      connectNulls={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Top Selling Items */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Star className="w-5 h-5" />
                <span>Top Selling Items</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Margherita Pizza</p>
                  <p className="text-sm text-muted-foreground">23 orders</p>
                </div>
                <Badge variant="secondary" className="bg-green-100 text-green-800">
                  +15%
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Caesar Salad</p>
                  <p className="text-sm text-muted-foreground">18 orders</p>
                </div>
                <Badge variant="secondary" className="bg-green-100 text-green-800">
                  +8%
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Chicken Alfredo</p>
                  <p className="text-sm text-muted-foreground">15 orders</p>
                </div>
                <Badge variant="secondary" className="bg-red-100 text-red-800">
                  -3%
                </Badge>
              </div>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium">Tiramisu</p>
                  <p className="text-sm text-muted-foreground">12 orders</p>
                </div>
                <Badge variant="secondary" className="bg-green-100 text-green-800">
                  +22%
                </Badge>
              </div>
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
                  <Star className="w-4 h-4 fill-yellow-400 text-yellow-400" />
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
