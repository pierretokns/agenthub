#!/bin/bash
# Manage cloud orchestrator daemon
# Usage: bash scripts/manage_orchestrator.sh [start|stop|restart|status|logs]

SERVICE_NAME="com.agenthub.cloud-orchestrator"
PLIST="$HOME/Library/LaunchAgents/com.agenthub.cloud-orchestrator.plist"
LOG_DIR="$HOME/.local/var/log/agenthub"

command=${1:-status}

case "$command" in
  start)
    echo "Starting $SERVICE_NAME..."
    launchctl start "$SERVICE_NAME"
    echo "✓ Started"
    ;;

  stop)
    echo "Stopping $SERVICE_NAME..."
    launchctl stop "$SERVICE_NAME"
    echo "✓ Stopped"
    ;;

  restart)
    echo "Restarting $SERVICE_NAME..."
    launchctl stop "$SERVICE_NAME" 2>/dev/null || true
    sleep 2
    launchctl start "$SERVICE_NAME"
    echo "✓ Restarted"
    ;;

  status)
    if launchctl list "$SERVICE_NAME" &>/dev/null; then
      echo "✓ $SERVICE_NAME is RUNNING"
      echo ""
      echo "Details:"
      launchctl list "$SERVICE_NAME"
    else
      echo "✗ $SERVICE_NAME is NOT running"
      echo ""
      echo "To start: launchctl load $PLIST"
    fi
    ;;

  logs)
    echo "Streaming logs from $LOG_DIR..."
    echo ""
    tail -f "$LOG_DIR"/orchestrator.*.log
    ;;

  logs-error)
    echo "Last 50 lines of error log:"
    tail -n 50 "$LOG_DIR/orchestrator.stderr.log"
    ;;

  logs-out)
    echo "Last 50 lines of output log:"
    tail -n 50 "$LOG_DIR/orchestrator.stdout.log"
    ;;

  config)
    echo "Plist location: $PLIST"
    echo ""
    echo "To edit:"
    echo "  vim $PLIST"
    echo ""
    echo "Then reload:"
    echo "  launchctl unload $PLIST && launchctl load $PLIST"
    ;;

  install)
    echo "Installing orchestrator daemon..."
    bash "$(dirname "$0")/install_launchctl.sh"
    ;;

  uninstall)
    echo "Removing $SERVICE_NAME..."
    launchctl unload "$PLIST" 2>/dev/null || true
    rm -f "$PLIST"
    echo "✓ Uninstalled"
    ;;

  *)
    echo "Cloud Orchestrator Daemon Manager"
    echo ""
    echo "Usage: bash scripts/manage_orchestrator.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start        - Start the daemon"
    echo "  stop         - Stop the daemon"
    echo "  restart      - Restart the daemon"
    echo "  status       - Show daemon status"
    echo "  logs         - Tail all logs"
    echo "  logs-error   - Show error log"
    echo "  logs-out     - Show output log"
    echo "  config       - Show config location"
    echo "  install      - Install the daemon"
    echo "  uninstall    - Uninstall the daemon"
    echo ""
    echo "Examples:"
    echo "  bash scripts/manage_orchestrator.sh status"
    echo "  bash scripts/manage_orchestrator.sh logs"
    echo "  bash scripts/manage_orchestrator.sh restart"
    ;;
esac
