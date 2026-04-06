"use client";

export default function Home() {
  if (typeof window !== "undefined") {
    window.top!.location.href = "/dashboard";
  }
  return null;
}