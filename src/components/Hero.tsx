import Image from 'next/image';
import { ArrowRight } from 'lucide-react';
import Link from 'next/link';

export function Hero() {
  return (
    <div className="relative w-full h-96 overflow-hidden rounded-xl mb-8">
      <Image
        src="https://v3b.fal.media/files/b/0a9f3351/-URZOoGy-_NfPdZ-cXqFZ_MYNkK0we.png"
        alt="Terra.OS Hero"
        fill
        className="object-cover"
        priority
      />
      <div className="absolute inset-0 bg-gradient-to-t from-[#0A0A0A] via-transparent to-transparent" />
      <div className="absolute bottom-0 left-0 p-8">
        <h1 className="text-4xl md:text-5xl font-display font-bold text-white mb-4">
          Terra.OS
        </h1>
        <p className="text-xl text-neutral-400 mb-6 max-w-2xl">
          System zarządzania Ziemią dla firm budowlanych.
        </p>
        <Link href="/kostorys" className="btn-primary inline-flex items-center gap-2">
          STARTUJMY <ArrowRight className="w-5 h-5" />
        </Link>
      </div>
    </div>
  );
}
