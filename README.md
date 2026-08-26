# AISFriends Vessel Tracker for Home Assistant

<p align="center">
  <img src="custom_components/aisfriends/brand/icon.png" alt="AISFriends icon" width="160">
</p>

A Home Assistant custom integration for tracking vessels from the AISFriends API by MMSI. It exposes each vessel as a GPS device tracker plus navigation, destination, ETA, and speed sensors.

## Installation

### HACS

1. Add this repository as a custom HACS repository with category **Integration**.
2. Install **AISFriends Vessel Tracker**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add Integration → AISFriends Vessel Tracker**.

### Manual

Copy `custom_components/aisfriends` into your Home Assistant `custom_components` directory and restart Home Assistant.

## Configuration

The UI config flow asks for your AISFriends bearer token, one or more 9-digit MMSI values, and a polling interval. Runtime options can be changed from the integration's **Configure** button without re-entering the API token.

## Entities

For each configured MMSI the integration creates a GPS device tracker and sensors for navigational status, destination, ETA, and speed over ground.

## Diagnostics and privacy

The API bearer token is not included in Home Assistant diagnostics or debug log messages. Diagnostics may include truncated API response data to help troubleshoot vessel parsing.

## Development

Validation mirrors the `ha-etoro` repository: Python/static checks, Home Assistant hassfest, HACS validation, and tag/manifest synchronization. Merging a pull request to `main` creates the next patch release automatically.
