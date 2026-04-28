export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  public: {
    Tables: {
      recipes: {
        Row: {
          created_at: string
          description: string
          duration_minutes: number
          embedding: string | null
          recipe_id: string
          servings: number
          source: string
          steps: Json
          tags: string[]
          title: string
        }
        Insert: {
          created_at?: string
          description: string
          duration_minutes: number
          embedding?: string | null
          recipe_id?: string
          servings: number
          source?: string
          steps?: Json
          tags?: string[]
          title: string
        }
        Update: {
          created_at?: string
          description?: string
          duration_minutes?: number
          embedding?: string | null
          recipe_id?: string
          servings?: number
          source?: string
          steps?: Json
          tags?: string[]
          title?: string
        }
        Relationships: []
      }
      sessions: {
        Row: {
          active_recipe_id: string | null
          canvas_state: Json
          conversation: Json
          created_at: string
          current_step: number | null
          last_active: string
          preferences: Json
          session_id: string
        }
        Insert: {
          active_recipe_id?: string | null
          canvas_state?: Json
          conversation?: Json
          created_at?: string
          current_step?: number | null
          last_active?: string
          preferences?: Json
          session_id?: string
        }
        Update: {
          active_recipe_id?: string | null
          canvas_state?: Json
          conversation?: Json
          created_at?: string
          current_step?: number | null
          last_active?: string
          preferences?: Json
          session_id?: string
        }
        Relationships: []
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      [_ in never]: never
    }
    Enums: {
      [_ in never]: never
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

export type Tables<T extends keyof Database["public"]["Tables"]> =
  Database["public"]["Tables"][T]["Row"]

export type TablesInsert<T extends keyof Database["public"]["Tables"]> =
  Database["public"]["Tables"][T]["Insert"]

export type TablesUpdate<T extends keyof Database["public"]["Tables"]> =
  Database["public"]["Tables"][T]["Update"]
