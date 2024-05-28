# Manual Onboarding for IOS-XE SDWAN Router

Manual Onboarding of SDWAN Router

## 1. Stop PnP Process

Stop the PnP process. Wait a moment until the the device has killed the process and is up and ready. 

```
pnpa service discovery stop
```

## 2. Configure System Settings

Configure the device with the matching system settings (org-name and vbond) and allocate its own identifiers. 

```
system
hostname ROUTER-1
system-ip 10.1.1.10
site-id 10
organization-name "ORG"
vbond 10.1.1.4
```

## 3. Create WAN Interface 

Configure an IP address to the WAN interface. 

```
interface GigabitEthernet0/0/1
description WAN
ip address 10.1.1.8 255.255.255.0
no shutdown
```

## 4. Create Tunnel Interface

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

## 5. Add Default Route

Add a default route to enable connectivity to wider network (if needed). 

```
ip route 0.0.0.0 0.0.0.0 10.1.1.1
```

## 6. Commit Changes 

Save configuration by committing it.

```
commit
```

## 7. Install Root Certificate

Install root certificate by importing the same certificate used for vManage. 

```
request platform software sdwan root-cert-chain install bootflash:root-ca-chain.pem
```

After completing Steps 1-7 the device can be confirmed from vManage dashboard. 
