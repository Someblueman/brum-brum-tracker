# brum-brum-tracker

## Project Guide: The "Brum Brum" Overhead Plane Tracker

This document outlines the concept, technical strategy, and deployment steps for creating a personalized, web-based plane spotter for a toddler. The goal is to create a simple, engaging display that shows when an airplane is about to pass overhead, complete with a directional arrow, a picture of the plane, a sound notification, and fun flight data like height and speed.

### The Concept & High-Level Strategy

The core idea is to build a small website that tracks flights in real-time near a specific location (your home).

This project is divided into two main components:
 -The Backend (The Brains): A program running on a home computer (like a Mac Mini or Raspberry Pi) that constantly fetches live flight data from a public API. It will do the "heavy lifting" of figuring out which planes are nearby and likely visible.
 -The Frontend (The Display): A simple, visual webpage displayed on an old iPad. This will show the fun stuff: an arrow pointing to the plane, a picture of the plane, its altitude and speed, and it will play a sound alert.

How It Works: The Workflow
 -Start Backend: You run the backend script on your home computer. It starts a local server and begins polling for flight data.
 -Open Frontend: You open the webpage on the iPad. It connects to the backend script.
 -Plane Approaches: The backend script identifies a plane that is getting close and is high enough in the sky to be visible.
 -Data is Sent: The backend fetches a picture and key flight details (altitude, speed, etc.) for that specific plane and sends all the relevant information to the iPad in real-time.
 -"Brum Brum!": The iPad's webpage receives the data, plays a "brum brum" sound, points an arrow towards the plane, and displays its picture and other fun facts.
