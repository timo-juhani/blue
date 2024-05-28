# Blue

## Introduction

## Installation

## CA Certificate

If you need to manually manage certs using openssl CLI commands this might come handy.

````
# Create CA private key and certificate
openssl req -x509 -newkey rsa:4096 -keyout ca.key -out ca.crt -days 3650 -nodes
````

The ca.crt file is the local root certificate in this case. And the one that needs to be installed 
on the SDWAN router that you're onboarding. 

Upload the certificate on an USB stick and plug the stick in the router for installation

## Power Up And Wait Until Boot Finishes

Wait until the device has powered on properly. You can monitor the process via your console cable. 
After the device is up hit Enter to break the PnP process. 

## Appendix: Manual Onboarding for IOS-XE SDWAN Router

Manual Onboarding of SDWAN Router.

### 1. Stop PnP Process

Stop the PnP process. Wait a moment until the the device has killed the process and is up and ready. 

```
pnpa service discovery stop
```

### 2. Configure System Settings

Configure the device with the matching system settings (org-name and vbond) and allocate its own identifiers. 

```
system
hostname ROUTER-1
system-ip 10.1.1.10
site-id 10
organization-name "ORG"
vbond 10.1.1.4
```

### 3. Create WAN Interface 

Configure an IP address to the WAN interface. 

```
interface GigabitEthernet0/0/1
description WAN
ip address 10.1.1.8 255.255.255.0
no shutdown
```

### 4. Create Tunnel Interface

Create the tunnel interface and tie it to the WAN interface.

```
interface Tunnel1
ip unnumbered GigabitEthernet0/0/1
tunnel source GigabitEthernet0/0/1
tunnel mode sdwan
no shutdown
```

Allocate TLOC color to the WAN interface used for the tunnel. 

```
sdwan
interface GigabitEthernet0/0/1
tunnel-interface
encapsulation ipsec
color blue
```

### 5. Add Default Route

Add a default route to enable connectivity to wider network (if needed). 

```
ip route 0.0.0.0 0.0.0.0 10.1.1.1
```

### 6. Commit Changes 

Save configuration by committing it.

```
commit
```

### 7. Install Root Certificate

Install root certificate. 

```
request platform software sdwan root-cert-chain install bootflash:root-ca-chain.pem
```

After completing Steps 1-7 the device can be confirmed from vManage dashboard. 
