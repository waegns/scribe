# Test Lab 2

**Date:** 2026-05-17 20:52

## Objective
Testing Functionality

## Raw Output
```text
ipconfig
IPv4 Address . . . : 192.168.1.50
Default Gateway . . : 192.168.1.1
```

## AI Analysis
### Observation:
The command `ipconfig` was executed, displaying the IPv4 address and default gateway for a network interface on the device. The IP address is `192.168.1.50`, indicating that the system is likely connected to a private local area network (LAN) using a common home or small office subnet. The default gateway of `192.168.1.1` suggests that this router is providing internet connectivity and other network services.

### Lesson Learned:
Understanding how to use commands like `ipconfig` is crucial for diagnosing basic networking issues, such as checking if a device has an IP address or identifying the default gateway. This command reveals essential information about a computer's network configuration without requiring deep technical knowledge of networking protocols.

### Suggested Next Test:
To further investigate network connectivity and performance, run a `ping` test to the default gateway (`192.168.1.1`) and an external IP address (like Google DNS at 8.8.8.8). This will help determine if packets can reach both local and remote destinations.

### Interview Bullet:
Successfully used `ipconfig` to verify network settings, confirming the device's IPv4 address and default gateway, demonstrating foundational networking troubleshooting skills.
