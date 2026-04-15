"use client"

import { useState } from "react"
import {
  Bot,
  Check,
  Copy,
  ExternalLink,
  Key,
  Pencil,
  Plus,
  Trash2,
  Wifi,
} from "lucide-react"
import { toast } from "sonner"
import { formatDistanceToNow } from "date-fns"
import { fr } from "date-fns/locale"

import DashboardLayout from "../dashboard-layout"
import { PageHeader } from "@/components/page-header"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  useMcpTokens,
  useCreateMcpToken,
  useRevokeMcpToken,
  useRenameMcpToken,
  type McpToken,
} from "@/hooks/api/useMcpTokens"
import { useAuth } from "@/lib/auth"

const MCP_URL = process.env.NEXT_PUBLIC_MCP_URL || "https://budget.victorsmits.com/mcp"

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={copy} title="Copier">
      {copied ? <Check className="size-3.5 text-green-500" /> : <Copy className="size-3.5" />}
    </Button>
  )
}

function NewTokenDialog({ onCreated }: { onCreated: (token: McpToken) => void }) {
  const [label, setLabel] = useState("")
  const createToken = useCreateMcpToken()

  const submit = async () => {
    const result = await createToken.mutateAsync(label.trim())
    setLabel("")
    onCreated(result)
  }

  return (
    <div className="flex gap-2">
      <Input
        placeholder="Nom du token (ex: claude.ai, Claude Desktop)"
        value={label}
        onChange={(e) => setLabel(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        className="flex-1"
      />
      <Button onClick={submit} disabled={createToken.isPending}>
        <Plus className="mr-2 size-4" />
        Créer
      </Button>
    </div>
  )
}

function TokenRow({ token, onRevoke }: { token: McpToken; onRevoke: (id: string) => void }) {
  const [editing, setEditing] = useState(false)
  const [label, setLabel] = useState(token.label)
  const rename = useRenameMcpToken()
  const revoke = useRevokeMcpToken()

  const saveLabel = async () => {
    await rename.mutateAsync({ id: token.id, label })
    setEditing(false)
  }

  const handleRevoke = () => {
    if (confirm(`Révoquer le token "${token.label || "sans nom"}" ?`)) {
      revoke.mutate(token.id, { onSuccess: () => onRevoke(token.id) })
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-background/70 p-3">
      <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
        <Key className="size-4" />
      </span>

      <div className="min-w-0 flex-1">
        {editing ? (
          <div className="flex gap-2">
            <Input
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && saveLabel()}
              className="h-7 text-sm"
              autoFocus
            />
            <Button size="sm" variant="ghost" onClick={saveLabel} disabled={rename.isPending}>
              <Check className="size-3.5" />
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-medium">{token.label || <span className="text-muted-foreground italic">Sans nom</span>}</p>
            {token.oauth_client && (
              <Badge variant="secondary" className="shrink-0 text-xs">
                <Wifi className="mr-1 size-3" />
                OAuth
              </Badge>
            )}
            <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0" onClick={() => setEditing(true)}>
              <Pencil className="size-3" />
            </Button>
          </div>
        )}
        <p className="text-xs text-muted-foreground">
          Créé {formatDistanceToNow(new Date(token.created_at), { addSuffix: true, locale: fr })}
          {token.last_used_at && (
            <> · Utilisé {formatDistanceToNow(new Date(token.last_used_at), { addSuffix: true, locale: fr })}</>
          )}
        </p>
      </div>

      <Button
        variant="ghost"
        size="icon"
        className="h-8 w-8 shrink-0 text-destructive hover:bg-destructive/10"
        onClick={handleRevoke}
        disabled={revoke.isPending}
        title="Révoquer"
      >
        <Trash2 className="size-4" />
      </Button>
    </div>
  )
}

function NewTokenSecret({ token, onDismiss }: { token: McpToken; onDismiss: () => void }) {
  const [copied, setCopied] = useState(false)

  const copy = async () => {
    await navigator.clipboard.writeText(token.token!)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
    toast.success("Token copié !")
  }

  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 dark:border-amber-700 dark:bg-amber-950/30">
      <p className="mb-2 text-sm font-semibold text-amber-800 dark:text-amber-300">
        Token créé — copiez-le maintenant, il ne sera plus affiché.
      </p>
      <div className="mb-3 flex items-center gap-2 rounded-md border bg-background p-2 font-mono text-xs break-all">
        <span className="flex-1">{token.token}</span>
        <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" onClick={copy}>
          {copied ? <Check className="size-3.5 text-green-500" /> : <Copy className="size-3.5" />}
        </Button>
      </div>
      <Button variant="outline" size="sm" onClick={onDismiss}>
        J'ai copié le token
      </Button>
    </div>
  )
}

export default function SettingsPage() {
  const { user } = useAuth()
  const tokens = useMcpTokens()
  const [newToken, setNewToken] = useState<McpToken | null>(null)

  const handleCreated = (token: McpToken) => {
    setNewToken(token)
  }

  return (
    <DashboardLayout>
      <div className="space-y-6 pb-6">
        <PageHeader title="Paramètres" subtitle="Gérez votre compte et vos connexions." />

        {/* MCP section */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <span className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Bot className="size-5" />
              </span>
              <div>
                <CardTitle className="text-base">Connexion MCP</CardTitle>
                <CardDescription>
                  Connectez Claude AI à votre Budget Bo pour interroger vos finances.
                </CardDescription>
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Connection info */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">URL du serveur MCP</Label>
              <div className="flex items-center gap-2 rounded-md border bg-muted/40 px-3 py-2 font-mono text-sm">
                <span className="flex-1 break-all">{MCP_URL}</span>
                <CopyButton text={MCP_URL} />
              </div>

              <div className="rounded-lg border bg-muted/20 p-4 text-sm space-y-2">
                <p className="font-medium flex items-center gap-2">
                  <ExternalLink className="size-4" /> Comment connecter Claude
                </p>
                <ol className="list-decimal space-y-1 pl-5 text-muted-foreground">
                  <li>
                    Sur <strong>claude.ai</strong> : Paramètres → Connecteurs MCP → Ajouter un serveur → coller l'URL ci-dessus. L'authentification OAuth se fait automatiquement.
                  </li>
                  <li>
                    Sur <strong>Claude Desktop</strong> : créez un token ci-dessous, puis ajoutez dans <code className="rounded bg-muted px-1">claude_desktop_config.json</code> :
                    <pre className="mt-1 rounded-md bg-muted p-2 text-xs overflow-x-auto">{`{
  "mcpServers": {
    "budget-bo": {
      "url": "${MCP_URL}",
      "headers": { "Authorization": "Bearer <votre-token>" }
    }
  }
}`}</pre>
                  </li>
                  <li>
                    Sur <strong>Claude Code</strong> : <code className="rounded bg-muted px-1">claude mcp add budget-bo {MCP_URL} --header "Authorization: Bearer &lt;token&gt;"</code>
                  </li>
                </ol>
              </div>
            </div>

            {/* Tokens list */}
            <div className="space-y-3">
              <Label className="text-sm font-medium">Tokens d'accès</Label>

              {newToken && (
                <NewTokenSecret
                  token={newToken}
                  onDismiss={() => setNewToken(null)}
                />
              )}

              <NewTokenDialog onCreated={handleCreated} />

              {tokens.isLoading && (
                <p className="text-sm text-muted-foreground">Chargement…</p>
              )}

              {tokens.data && tokens.data.length === 0 && (
                <p className="rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">
                  Aucun token actif. Créez-en un pour vous connecter.
                </p>
              )}

              <div className="space-y-2">
                {(tokens.data || []).map((token) => (
                  <TokenRow
                    key={token.id}
                    token={token}
                    onRevoke={() => {}}
                  />
                ))}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Profile section */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Profil</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex items-center gap-3">
              <span className="w-24 text-muted-foreground">Email</span>
              <span>{user?.email}</span>
            </div>
            {user?.display_name && (
              <div className="flex items-center gap-3">
                <span className="w-24 text-muted-foreground">Nom</span>
                <span>{user.display_name}</span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}
