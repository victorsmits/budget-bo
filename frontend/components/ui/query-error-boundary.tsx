import { Component, ErrorInfo, ReactNode } from "react"
import { Button } from "./button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./card"

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
}

export class QueryErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
  }

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo)
  }

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <Card className="mx-auto max-w-md">
          <CardHeader>
            <CardTitle className="text-red-600">Une erreur est survenue</CardTitle>
            <CardDescription>
              {this.state.error?.message || "Une erreur inattendue s'est produite"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              onClick={() => {
                this.setState({ hasError: false, error: undefined })
                window.location.reload()
              }}
              variant="outline"
              className="w-full"
            >
              Actualiser la page
            </Button>
          </CardContent>
        </Card>
      )
    }

    return this.props.children
  }
}
